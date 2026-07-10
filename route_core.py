"""
route_core.py — Motor de ruteo con base central, entregas y recogidas,
ventanas de tiempo (prioritarios) y EQUILIBRIO POR TIEMPO.

Modelo (OR-Tools): nodo 0 = base; el resto = pedidos (entrega/recogida).
Todos los repartidores salen y regresan a la base. El coste es el TIEMPO
(viaje + servicio). Se minimiza el makespan (que todos terminen a una hora
parecida) para que nadie quede rezagado, y se respetan los plazos de los
prioritarios como ventanas de tiempo. Las recogidas se acumulan y se
descargan al volver a la base (no afectan al ruteo salvo que haya capacidad).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

EARTH_R = 6_371_000.0


def haversine_m(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*EARTH_R*math.asin(math.sqrt(h))


@dataclass
class RoutePlan:
    vehicle: int
    stops: list          # [{'idx':int,'arrival_min':float}]
    route_min: float
    end_min: float
    n_entregas: int
    n_recogidas: int


@dataclass
class Plan:
    routes: list = field(default_factory=list)
    dropped: list = field(default_factory=list)
    k: int = 0
    total_min: float = 0.0
    makespan_min: float = 0.0
    start_min: int = 0


def _matrix_min(coords, speed_kmh, service_min):
    """Matriz de tiempos (min): viaje haversine + servicio en el destino."""
    n = len(coords)
    mpm = speed_kmh * 1000 / 60.0  # metros por minuto
    M = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            travel = haversine_m(coords[i], coords[j]) / mpm
            serv = service_min if j != 0 else 0  # sin servicio al volver a la base
            M[i][j] = int(round(travel + serv))
    return M


def solve_vrp(stops, depot, k, *, start_min=480, speed_kmh=22.0, service_min=4.0,
              shift_min=600, time_limit_s=8, span_coeff=100):
    """
    stops: lista de dicts con 'lat','lon','tipo'('entrega'/'recogida'),
           'deadline_min' (min absolutos desde medianoche, o None).
    depot: (lat, lon). k: nº de repartidores. start_min: hora de salida (min).
    Devuelve Plan. Si algún pedido no cabe, queda en 'dropped'.
    """
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    coords = [depot] + [(s["lat"], s["lon"]) for s in stops]
    n = len(coords)
    M = _matrix_min(coords, speed_kmh, service_min)

    mgr = pywrapcp.RoutingIndexManager(n, k, 0)
    routing = pywrapcp.RoutingModel(mgr)
    cb = routing.RegisterTransitCallback(
        lambda a, b: M[mgr.IndexToNode(a)][mgr.IndexToNode(b)])
    routing.SetArcCostEvaluatorOfAllVehicles(cb)

    routing.AddDimension(cb, shift_min, shift_min, True, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    time_dim.SetGlobalSpanCostCoefficient(span_coeff)  # equilibrio por tiempo

    # ventanas de tiempo de los prioritarios (cota superior de llegada)
    for i, s in enumerate(stops, start=1):
        dl = s.get("deadline_min")
        if dl is not None:
            ub = max(0, int(dl - start_min))
            time_dim.CumulVar(mgr.NodeToIndex(i)).SetMax(min(ub, shift_min))

    # permitir descartar un pedido (con penalización alta) si no cabe
    for i in range(1, n):
        routing.AddDisjunction([mgr.NodeToIndex(i)], 1_000_000)

    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.FromSeconds(max(1, time_limit_s))

    sol = routing.SolveWithParameters(p)
    plan = Plan(k=k, start_min=start_min)
    if sol is None:
        plan.dropped = list(range(len(stops)))
        return plan

    served = set()
    for v in range(k):
        idx = routing.Start(v)
        route, end = [], 0
        while not routing.IsEnd(idx):
            node = mgr.IndexToNode(idx)
            if node != 0:
                arr = sol.Min(time_dim.CumulVar(idx))
                route.append({"idx": node-1, "arrival_min": start_min + arr})
                served.add(node-1)
            idx = sol.Value(routing.NextVar(idx))
        end = sol.Min(time_dim.CumulVar(idx))  # llegada de vuelta a la base
        if route:
            ne = sum(1 for r in route if stops[r["idx"]]["tipo"] == "entrega")
            nr = len(route) - ne
            plan.routes.append(RoutePlan(v, route, end, start_min+end, ne, nr))
    plan.dropped = [i for i in range(len(stops)) if i not in served]
    plan.routes.sort(key=lambda r: r.vehicle)
    plan.k = len(plan.routes)
    plan.makespan_min = max((r.route_min for r in plan.routes), default=0)
    plan.total_min = sum(r.route_min for r in plan.routes)
    return plan


def find_min_k(stops, depot, kmax, **kw):
    """Menor nº de repartidores que sirve todos los pedidos dentro de la jornada."""
    for k in range(1, kmax+1):
        plan = solve_vrp(stops, depot, k, **kw)
        if not plan.dropped and plan.makespan_min <= kw.get("shift_min", 600):
            return plan
    return solve_vrp(stops, depot, kmax, **kw)

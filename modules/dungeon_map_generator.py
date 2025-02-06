# dungeon_map_generator.py
import random
import math
import uuid
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import networkx as nx

logger = logging.getLogger(__name__)

# Configuration Constants =====================================================
DICE_TYPES = ['d4', 'd6', 'd8', 'd10', 'd12', 'd20']
DICE_ROOM_TYPES = {
    'd4': 'Small side room or larger corridor',
    'd6': 'Rectangular chamber',
    'd8': 'Irregularly-shaped chamber',
    'd10': 'Main objective or passage leading deeper',
    'd12': 'Special feature (river, chasm, tunnel)',
    'd20': 'Grand hall or important chamber'
}
ROOM_FEATURES = [
    'Treasure', 'Trap', 'Secret Door',
    'Puzzle', 'Monster Encounter', 'Hidden Passage'
]
POSITION_JITTER = 4.0  # Max position variation from cluster center
CLUSTER_SPREAD = 6.0   # Max distance between cluster centers

# Data Structures =============================================================
@dataclass
class Node:
    id: str
    dice: str
    room_type: str
    position: Tuple[float, float]
    sub_nodes: List['Node']
    is_entrance: bool
    key: Optional[str]
    features: List[str]

@dataclass
class Edge:
    start_id: str
    end_id: str

# Core Generation Functions ===================================================

def simulate_dice_drops() -> List[Node]:
    """
    Generate nodes with clustered positions for loops and random placement for others.
    """
    dice_counts = {'d4': 2, 'd6': 2, 'd8': 2, 'd10': 2, 'd12': 2, 'd20': 2}
    nodes = []

    # Create overlapping cluster centers
    main_center = (random.uniform(8, 12), random.uniform(10, 14))
    red_center = (
        main_center[0] + random.uniform(-CLUSTER_SPREAD/2, CLUSTER_SPREAD/2),
        main_center[1] + random.uniform(-CLUSTER_SPREAD/2, CLUSTER_SPREAD/2)
    )
    blue_center = (
        main_center[0] + random.uniform(-CLUSTER_SPREAD/2, CLUSTER_SPREAD/2),
        main_center[1] + random.uniform(-CLUSTER_SPREAD/2, CLUSTER_SPREAD/2)
    )

    for dice, count in dice_counts.items():
        for i in range(count):
            # Cluster loop nodes
            if dice in ['d6', 'd8', 'd10', 'd12', 'd20']:
                center = red_center if i == 0 else blue_center
                x = center[0] + random.uniform(-POSITION_JITTER, POSITION_JITTER)
                y = center[1] + random.uniform(-POSITION_JITTER, POSITION_JITTER)
            else:  # Non-loop nodes get semi-random placement
                base_x = main_center[0] + random.uniform(-CLUSTER_SPREAD, CLUSTER_SPREAD)
                base_y = main_center[1] + random.uniform(-CLUSTER_SPREAD, CLUSTER_SPREAD)
                x = base_x + random.uniform(-POSITION_JITTER, POSITION_JITTER)
                y = base_y + random.uniform(-POSITION_JITTER, POSITION_JITTER)

            nodes.append(Node(
                id=str(uuid.uuid4()),
                dice=dice,
                room_type="",
                position=(x, y),
                sub_nodes=[],
                is_entrance=False,
                key=None,
                features=[]
            ))
    return nodes

def _process_nodes(nodes: List[Node]) -> List[Node]:
    """Apply post-processing to generated nodes."""
    for i, node in enumerate(nodes, start=1):
        node.room_type = DICE_ROOM_TYPES[node.dice]
        node.features = random.sample(ROOM_FEATURES, random.randint(0, 2))
        node.key = f"Room {i}"
        if node.dice == 'd4' and not any(n.is_entrance for n in nodes):
            node.is_entrance = True
    return nodes

def segment_intersection(a: Tuple[float, float], b: Tuple[float, float],
                         c: Tuple[float, float], d: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    """Detect segment intersections with endpoint checking."""
    def ccw(A, B, C):
        return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

    intersect = ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)
    if not intersect:
        return None

    # Calculate intersection point
    A = np.array(a)
    B = np.array(b)
    C = np.array(c)
    D = np.array(d)
    BA = B - A
    DC = D - C
    denom = BA[0] * DC[1] - BA[1] * DC[0]
    if denom == 0:
        return None  # Parallel

    t = ((C[0] - A[0]) * DC[1] - (C[1] - A[1]) * DC[0]) / denom
    u = ((C[0] - A[0]) * BA[1] - (C[1] - A[1]) * BA[0]) / denom
    if 0 < t < 1 and 0 < u < 1:
        return (float(A[0] + t * BA[0]), float(A[1] + t * BA[1]))
    return None

def create_loops_and_connect(nodes: List[Node]) -> Tuple[List[Edge], List[Dict[str, Any]]]:
    """Create interconnected loops with organic connections."""
    edges: List[Edge] = []
    junctions: List[Dict[str, Any]] = []
    loops = []
    nodes_by_dice = {d: [] for d in DICE_TYPES}

    for node in nodes:
        nodes_by_dice[node.dice].append(node)

    # Create red and blue loops
    for color in ['red', 'blue']:
        try:
            loop_nodes = [
                nodes_by_dice['d6'][0 if color == 'red' else 1],
                nodes_by_dice['d8'][0 if color == 'red' else 1],
                nodes_by_dice['d10'][0 if color == 'red' else 1],
                nodes_by_dice['d12'][0 if color == 'red' else 1],
                nodes_by_dice['d20'][0 if color == 'red' else 1]
            ]

            # Create loop edges with occasional shortcuts
            for i in range(len(loop_nodes)):
                start = loop_nodes[i]
                end = loop_nodes[(i+1)%len(loop_nodes)]
                edges.append(Edge(start.id, end.id))

                # 30% chance to add a cross-loop connection
                if random.random() < 0.3 and i < len(loop_nodes)-1:
                    edges.append(Edge(start.id, loop_nodes[i+2].id))

            loops.append({
                'color': color,
                'node_ids': [n.id for n in loop_nodes],
                'keys': [n.key for n in loop_nodes]
            })
        except IndexError:
            logger.warning(f"Missing nodes for {color} loop")

    # Connect closest nodes between loops
    red_nodes = [n for loop in loops if loop['color'] == 'red' for n in loop['node_ids']]
    blue_nodes = [n for loop in loops if loop['color'] == 'blue' for n in loop['node_ids']]

    if red_nodes and blue_nodes:
        closest_pair = min(
            [(r, b) for r in red_nodes for b in blue_nodes],
            key=lambda pair: math.dist(
                next(n.position for n in nodes if n.id == pair[0]),
                next(n.position for n in nodes if n.id == pair[1])
            )
        )
        edges.append(Edge(*closest_pair))

    # Connect free nodes with bias towards nearby clusters
    used_ids = {nid for loop in loops for nid in loop['node_ids']}
    free_nodes = [n for n in nodes if n.id not in used_ids]

    for free in free_nodes:
        candidates = [
            n for n in nodes
            if n.id != free.id
               and (n.dice in ['d6', 'd8', 'd10'] or random.random() < 0.4)
        ]
        if candidates:
            closest = min(candidates,
                          key=lambda n: math.dist(free.position, n.position))
            edges.append(Edge(free.id, closest.id))

    # Detect intersections
    for i in range(len(edges)):
        for j in range(i+1, len(edges)):
            e1, e2 = edges[i], edges[j]
            if {e1.start_id, e1.end_id} & {e2.start_id, e2.end_id}:
                continue

            a = next(n.position for n in nodes if n.id == e1.start_id)
            b = next(n.position for n in nodes if n.id == e1.end_id)
            c = next(n.position for n in nodes if n.id == e2.start_id)
            d = next(n.position for n in nodes if n.id == e2.end_id)

            if point := segment_intersection(a, b, c, d):
                junctions.append({
                    'point': point,
                    'edges': (e1.start_id, e1.end_id, e2.start_id, e2.end_id),
                    'type': 'crossing' if random.random() < 0.7 else 'junction'
                })

    return edges, junctions

def connect_clusters(nodes: List[Node], edges: List[Edge]) -> List[Edge]:
    """Ensure connectivity with organic bridging."""
    G = nx.Graph()
    G.add_nodes_from(n.id for n in nodes)
    G.add_edges_from((e.start_id, e.end_id) for e in edges)

    extra_edges = []
    components = list(nx.connected_components(G))

    while len(components) > 1:
        # Find closest pair between components
        closest = None
        min_dist = float('inf')

        for i in range(len(components)):
            for j in range(i+1, len(components)):
                for n1 in components[i]:
                    pos1 = next(n.position for n in nodes if n.id == n1)
                    for n2 in components[j]:
                        pos2 = next(n.position for n in nodes if n.id == n2)
                        if (dist := math.dist(pos1, pos2)) < min_dist:
                            min_dist = dist
                            closest = (n1, n2)

        if closest:
            extra_edges.append(Edge(*closest))
            G.add_edge(*closest)
            components = list(nx.connected_components(G))

    # Add random organic bridges
    for _ in range(random.randint(1, 3)):
        n1, n2 = random.sample(nodes, 2)
        if not G.has_edge(n1.id, n2.id):
            extra_edges.append(Edge(n1.id, n2.id))
            G.add_edge(n1.id, n2.id)

    return extra_edges

def save_graph_image(nodes: List[Dict], edges: List[Dict], image_filename: str = "dungeon_graph.png"):
    """Visualize with force-directed layout."""
    G = nx.Graph()
    pos = {}

    for node in nodes:
        label = node.get('key', node['id'])
        G.add_node(label)
        pos[label] = node['position']

    for edge in edges:
        start = next(n['key'] for n in nodes if n['id'] == edge['start_id'])
        end = next(n['key'] for n in nodes if n['id'] == edge['end_id'])
        G.add_edge(start, end)

    plt.figure(figsize=(12, 16))
    nx.draw(G, pos, with_labels=True, node_size=400,
            font_size=8, alpha=0.8, edge_color='gray')
    plt.title("Organic Dungeon Layout")
    plt.savefig(image_filename)
    plt.close()

def generate_dungeon_map(*args, **kwargs) -> Dict[str, Any]:
    """Main generation process with enhanced logging."""
    logger.info("🗺️ Starting organic dungeon generation...")
    try:
        seed = random.randint(0, 100000)
        random.seed(seed)

        nodes = simulate_dice_drops()
        nodes = _process_nodes(nodes)

        edges, junctions = create_loops_and_connect(nodes)
        extra_edges = connect_clusters(nodes, edges)
        edges.extend(extra_edges)

        logger.info(f"🌐 Generated {len(nodes)} rooms with {len(edges)} connections")
        logger.info(f"🔄 Found {len(junctions)} organic intersections")

        return {
            "content": "Organic Dungeon Map",
            "metadata": {
                "nodes": [asdict(n) for n in nodes],
                "edges": [asdict(e) for e in edges],
                "junctions": junctions,
                "seed": seed,
                "stats": {
                    "total_rooms": len(nodes),
                    "connections": len(edges),
                    "entrances": sum(1 for n in nodes if n.is_entrance),
                    "crossings": sum(1 for j in junctions if j['type'] == 'crossing')
                }
            }
        }
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        return {"error": str(e)}
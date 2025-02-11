import random
import math
import uuid
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple  # Ensure this is present!
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import networkx as nx

# Import our doc writer for writing sections.
from modules.doc_writer import write_section

logger = logging.getLogger(__name__)

# Configuration Constants =====================================================
GRID_WIDTH = 8.5  # Standard US letter width in inches
GRID_HEIGHT = 11  # Standard US letter height in inches
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
POSITION_JITTER = 1.2
CLUSTER_SPREAD = 2.0
MARGIN = 0.5

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

@dataclass
class Junction:
    point: Tuple[float, float]
    edges: Tuple[str, str, str, str]
    type: str

# Core Generation Functions ===================================================

def simulate_dice_drops() -> List[Node]:
    """Generate nodes with paper-constrained positions"""
    dice_counts = {'d4': 2, 'd6': 2, 'd8': 2, 'd10': 2, 'd12': 2, 'd20': 2}
    nodes = []

    # Center clusters with small random offset
    main_center = (
        GRID_WIDTH / 2 + random.uniform(-0.5, 0.5),
        GRID_HEIGHT / 2 + random.uniform(-0.5, 0.5)
    )
    red_center = (
        np.clip(main_center[0] + random.uniform(-CLUSTER_SPREAD, CLUSTER_SPREAD),
                MARGIN, GRID_WIDTH - MARGIN),
        np.clip(main_center[1] + random.uniform(-CLUSTER_SPREAD, CLUSTER_SPREAD),
                MARGIN, GRID_HEIGHT - MARGIN)
    )
    blue_center = (
        np.clip(main_center[0] + random.uniform(-CLUSTER_SPREAD, CLUSTER_SPREAD),
                MARGIN, GRID_WIDTH - MARGIN),
        np.clip(main_center[1] + random.uniform(-CLUSTER_SPREAD, CLUSTER_SPREAD),
                MARGIN, GRID_HEIGHT - MARGIN)
    )

    for dice, count in dice_counts.items():
        for i in range(count):
            if dice in ['d6', 'd8', 'd10', 'd12', 'd20']:
                center = red_center if i == 0 else blue_center
                x = np.clip(
                    center[0] + random.uniform(-POSITION_JITTER, POSITION_JITTER),
                    MARGIN,
                    GRID_WIDTH - MARGIN
                )
                y = np.clip(
                    center[1] + random.uniform(-POSITION_JITTER, POSITION_JITTER),
                    MARGIN,
                    GRID_HEIGHT - MARGIN
                )
            else:
                x = np.clip(
                    random.uniform(MARGIN, GRID_WIDTH - MARGIN),
                    MARGIN,
                    GRID_WIDTH - MARGIN
                )
                y = np.clip(
                    random.uniform(MARGIN, GRID_HEIGHT - MARGIN),
                    MARGIN,
                    GRID_HEIGHT - MARGIN
                )

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
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    intersect = ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)
    if not intersect:
        return None
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
        return float(A[0] + t * BA[0]), float(A[1] + t * BA[1])
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
            # Create loop edges
            for i in range(len(loop_nodes)):
                start = loop_nodes[i]
                end = loop_nodes[(i + 1) % len(loop_nodes)]
                edges.append(Edge(start.id, end.id))
            loops.append({
                'color': color,
                'node_ids': [n.id for n in loop_nodes],
                'keys': [n.key for n in loop_nodes]
            })
        except IndexError:
            logger.warning(f"Missing nodes for {color} loop")
    # Connect free nodes
    used_ids = {nid for loop in loops for nid in loop['node_ids']}
    free_nodes = [n for n in nodes if n.id not in used_ids]
    for free in free_nodes:
        candidates = [n for n in nodes if n.id != free.id]
        if candidates:
            closest = min(candidates, key=lambda n: math.dist(free.position, n.position))
            edges.append(Edge(free.id, closest.id))
    # Detect intersections
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
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
        closest = None
        min_dist = float('inf')
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
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
    # Add random bridges
    for _ in range(random.randint(1, 2)):  # Reduced from 3
        n1, n2 = random.sample(nodes, 2)
        if not G.has_edge(n1.id, n2.id):
            extra_edges.append(Edge(n1.id, n2.id))
            G.add_edge(n1.id, n2.id)
    return extra_edges

def save_graph_image(nodes: List[Dict], edges: List[Dict], loops: List[Dict],
                     image_filename: str = "dungeon_graph.png"):
    """Visualize with paper-constrained layout."""
    plt.figure(figsize=(GRID_WIDTH, GRID_HEIGHT), dpi=300)
    G = nx.Graph()
    pos = {}
    node_colors = []
    # Build nodes with position clamping
    for node in nodes:
        label = node['key']
        G.add_node(label)
        pos[label] = (
            np.clip(node['position'][0], MARGIN, GRID_WIDTH - MARGIN),
            np.clip(node['position'][1], MARGIN, GRID_HEIGHT - MARGIN)
        )
        # Color coding
        if node['is_entrance']:
            node_colors.append('#90EE90')  # Light green
        else:
            in_red = any(node['id'] in loop['node_ids'] for loop in loops if 'red' in loop.values())
            in_blue = any(node['id'] in loop['node_ids'] for loop in loops if 'blue' in loop.values())
            if in_red and in_blue:
                node_colors.append('#FFB6C1')  # Overlap
            elif in_red:
                node_colors.append('#FF9999')  # Red loop
            elif in_blue:
                node_colors.append('#99CCFF')  # Blue loop
            else:
                node_colors.append('#F0F0F0')  # Neutral
    # Build edges
    for edge in edges:
        start = next(n['key'] for n in nodes if n['id'] == edge['start_id'])
        end = next(n['key'] for n in nodes if n['id'] == edge['end_id'])
        G.add_edge(start, end)
    # Draw with paper constraints
    nx.draw(G, pos, with_labels=True, node_size=250,
            font_size=5, alpha=0.9, edge_color='#333333',
            node_color=node_colors, linewidths=0.3)
    plt.xlim(0, GRID_WIDTH)
    plt.ylim(0, GRID_HEIGHT)
    plt.title("Dungeon Map", fontsize=8)
    plt.tight_layout(pad=0.3)
    plt.savefig(image_filename, bbox_inches='tight')
    plt.close()

def generate_dungeon_map(*args, **kwargs) -> Dict[str, Any]:
    """Main generation process with error handling."""
    result: Dict[str, Any] = {
        "content": "",  # Will be updated with a generated summary.
        "metadata": {
            "nodes": [],
            "edges": [],
            "junctions": [],
            "loops": [],
            "seed": None,
            "stats": {
                "total_rooms": 0,
                "connections": 0,
                "entrances": 0,
                "crossings": 0,
                "junctions": 0
            }
        }
    }
    try:
        logger.info("🗺️ Starting dungeon generation...")
        seed = random.randint(0, 100000)
        random.seed(seed)

        nodes = simulate_dice_drops()
        nodes = _process_nodes(nodes)

        edges, junctions = create_loops_and_connect(nodes)
        extra_edges = connect_clusters(nodes, edges)
        edges.extend(extra_edges)

        # Convert junctions to objects.
        junction_objects = [
            Junction(
                point=j['point'],
                edges=j['edges'],
                type=j['type']
            ) for j in junctions
        ]

        # Detect loops using networkx cycle_basis.
        edge_tuples = [(e.start_id, e.end_id) for e in edges]
        G = nx.Graph(edge_tuples)
        loops = [{'node_ids': cycle, 'color': 'red' if i == 0 else 'blue'}
                 for i, cycle in enumerate(nx.cycle_basis(G)) if len(cycle) >= 3]

        # Update result metadata.
        result['metadata'].update({
            "nodes": [asdict(n) for n in nodes],
            "edges": [asdict(e) for e in edges],
            "junctions": [asdict(j) for j in junction_objects],
            "loops": loops,
            "seed": seed,
            "stats": {
                "total_rooms": len(nodes),
                "connections": len(edges),
                "entrances": sum(1 for n in nodes if n.is_entrance),
                "crossings": sum(1 for j in junction_objects if j.type == 'crossing'),
                "junctions": len(junction_objects)
            }
        })

        # Build a descriptive summary for the dungeon map.
        room_list = _format_room_list(result['metadata']['nodes'])
    connection_list = _format_connection_list(result['metadata']['edges'], nodes)
    junction_list = _format_junction_list(result['metadata']['junctions'], edges, nodes)
    loop_list = _format_loop_list(result['metadata']['loops'], nodes)

    # Build comprehensive content
    dungeon_map_content = (
        "## Dungeon Map Overview\n\n"
        f"{stats_summary}\n\n"
        "## Room Directory\n"
        f"{room_list}\n\n"
        "## Connections\n"
        f"{connection_list}\n\n"
        "## Junctions & Crossings\n"
        f"{junction_list}\n\n"
        "## Loops\n"
        f"{loop_list}\n\n"
        "## Map Visualization\n"
        "![Dungeon Map](./dungeon_graph.png)"
    )

    # Write outputs
    write_section("dungeon_map", dungeon_map_content)
    save_graph_image(
        result['metadata']['nodes'],
        result['metadata']['edges'],
        result['metadata']['loops']
    )

        stats = result['metadata']['stats']
        loop_info = f"{len(loops)} loops" if loops else "no loops"
        dungeon_map_content = (
            f"The dungeon map was generated using seed {seed}.\n\n"
            f"It consists of {stats['total_rooms']} rooms connected by {stats['connections']} corridors.\n"
            f"There are {stats['entrances']} designated entrances, {stats['crossings']} crossings, and {stats['junctions']} junctions.\n"
            f"Additionally, the map contains {loop_info}.\n"
            "This intricate layout provides numerous paths and hidden passages, creating a rich environment for exploration."
        )

        # Update the content in the result with the generated summary.
        result["content"] = dungeon_map_content

        # Write the dungeon map content to a dungeon_map.md file.
        write_section("dungeon_map", dungeon_map_content)

    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        result['error'] = str(e)

    return result


def _format_room_list(nodes: List[Dict]) -> str:
    """Generate markdown list of rooms with details"""
    return "\n".join(
        f"- **{n['key']}**: {n['room_type']} "
        f"(Features: {', '.join(n['features'])}, "
        f"Position: ({n['position'][0]:.1f}, {n['position'][1]:.1f})"
        for n in nodes
    )

def _format_connection_list(edges: List[Dict], nodes: List[Node]) -> str:
    """Generate connection list with room names"""
    id_to_key = {n.id: n.key for n in nodes}
    return "\n".join(
        f"- {id_to_key[e['start_id']]} to {id_to_key[e['end_id']]}"
        for e in edges
    )

def _format_junction_list(junctions: List[Dict], edges: List[Edge], nodes: List[Node]) -> str:
    """Format junction details with room relationships"""
    id_to_key = {n.id: n.key for n in nodes}
    edge_map = {(e.start_id, e.end_id): (id_to_key[e.start_id], id_to_key[e.end_id]) for e in edges}

    return "\n".join(
        f"- {j['type'].title()} at ({j['point'][0]:.1f}, {j['point'][1]:.1f}) "
        f"connecting {edge_map[(j['edges'][0], j['edges'][1])]} "
        f"and {edge_map[(j['edges'][2], j['edges'][3])]}"
        for j in junctions
    )

def _format_loop_list(loops: List[Dict], nodes: List[Node]) -> str:
    """Format loop information"""
    id_to_key = {n.id: n.key for n in nodes}
    return "\n".join(
        f"- {loop['color'].title()} Loop: {', '.join(id_to_key[nid] for nid in loop['node_ids'])}"
        for loop in loops
    )
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
    Generate a fixed set of node positions corresponding to:
      2 x d4, 2 x d6, 2 x d8, 2 x d10, 2 x d12, and 1 x d20.
    """
    dice_counts = {
        'd4': 2,
        'd6': 2,
        'd8': 2,
        'd10': 2,
        'd12': 2,
        'd20': 1
    }
    nodes = []
    for dice, count in dice_counts.items():
        for _ in range(count):
            node = Node(
                id=str(uuid.uuid4()),
                dice=dice,
                room_type="",  # To be set in _process_nodes
                position=(random.uniform(0, 16), random.uniform(0, 22)),
                sub_nodes=[],
                is_entrance=False,
                key=None,
                features=[]
            )
            nodes.append(node)
    return nodes

def _process_nodes(nodes: List[Node]) -> List[Node]:
    """Apply post-processing to generated nodes."""
    for i, node in enumerate(nodes, start=1):
        node.room_type = DICE_ROOM_TYPES[node.dice]
        node.features = random.sample(ROOM_FEATURES, random.randint(0, 2))
        # Assign a human-friendly key (e.g., "Room 1")
        node.key = f"Room {i}"
        # Designate an entrance if no node is yet an entrance and if the node is a d4 (small room)
        if node.dice == 'd4' and not any(n.is_entrance for n in nodes):
            node.is_entrance = True
    return nodes

def segment_intersection(a: Tuple[float, float], b: Tuple[float, float],
                         c: Tuple[float, float], d: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    """
    Check if line segment ab intersects cd.
    Returns the intersection point (x, y) if they intersect (and not at endpoints), else None.
    """
    def ccw(A, B, C):
        return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

    if ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d):
        A = np.array(a)
        B = np.array(b)
        C = np.array(c)
        D = np.array(d)
        BA = B - A
        DC = D - C
        denominator = BA[0] * DC[1] - BA[1] * DC[0]
        if denominator == 0:
            return None  # Parallel lines
        t = ((C[0] - A[0]) * DC[1] - (C[1] - A[1]) * DC[0]) / denominator
        inter_point = A + t * BA
        # Exclude intersections exactly at endpoints
        if (np.allclose(inter_point, A) or np.allclose(inter_point, B) or
                np.allclose(inter_point, C) or np.allclose(inter_point, D)):
            return None
        return (float(inter_point[0]), float(inter_point[1]))
    return None

def create_loops_and_connect(nodes: List[Node]) -> Tuple[List[Edge], List[Dict[str, Any]]]:
    """
    Create loops using the following procedure:
      - For a complete set, form a loop that connects: d6 -> d8 -> d10 -> d12 -> d20, then back to the starting d6.
      - If there are 10+ nodes and at least one complete set exists, form as many loops as possible.
    Then, for any nodes not used in a loop (free-floating), connect each to its nearest neighbor.
    Also, detect intersections between edges (which indicate junctions/traversals).
    Returns a tuple: (list of edges, list of junction records).
    """
    edges: List[Edge] = []
    junctions: List[Dict[str, Any]] = []
    loops = []

    # Group nodes by dice type
    nodes_by_dice = {d: [] for d in DICE_TYPES}
    for node in nodes:
        nodes_by_dice[node.dice].append(node)

    # Determine the number of complete loops we can form
    num_loops = min(
        len(nodes_by_dice['d6']),
        len(nodes_by_dice['d8']),
        len(nodes_by_dice['d10']),
        len(nodes_by_dice['d12']),
        len(nodes_by_dice['d20'])
    )
    # Form loops only if there are at least 10 nodes and at least one complete set exists.
    if len(nodes) >= 10 and num_loops > 0:
        for i in range(num_loops):
            d6_node = nodes_by_dice['d6'][i]
            d8_node = nodes_by_dice['d8'][i]
            d10_node = nodes_by_dice['d10'][i]
            d12_node = nodes_by_dice['d12'][i]
            d20_node = nodes_by_dice['d20'][i]
            # Create loop edges:
            edges.append(Edge(start_id=d6_node.id, end_id=d8_node.id))
            edges.append(Edge(start_id=d8_node.id, end_id=d10_node.id))
            edges.append(Edge(start_id=d10_node.id, end_id=d12_node.id))
            edges.append(Edge(start_id=d12_node.id, end_id=d20_node.id))
            edges.append(Edge(start_id=d20_node.id, end_id=d6_node.id))
            loops.append({
                'loop_keys': [d6_node.key, d8_node.key, d10_node.key, d12_node.key, d20_node.key],
                'node_ids': [d6_node.id, d8_node.id, d10_node.id, d12_node.id, d20_node.id]
            })

    # Identify free nodes (not used in any loop)
    used_ids = {nid for loop in loops for nid in loop['node_ids']}
    free_nodes = [node for node in nodes if node.id not in used_ids]

    # Connect each free-floating node to its nearest neighbor.
    for free in free_nodes:
        closest = None
        min_dist = float('inf')
        for node in nodes:
            if node.id == free.id:
                continue
            dist = np.linalg.norm(np.array(free.position) - np.array(node.position))
            if dist < min_dist:
                min_dist = dist
                closest = node
        if closest:
            edges.append(Edge(start_id=free.id, end_id=closest.id))

    # Detect intersections (junctions/traversals) between edges.
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            e1 = edges[i]
            e2 = edges[j]
            # Skip if edges share an endpoint.
            if (e1.start_id in [e2.start_id, e2.end_id] or
                    e1.end_id in [e2.start_id, e2.end_id]):
                continue
            a = next(node.position for node in nodes if node.id == e1.start_id)
            b = next(node.position for node in nodes if node.id == e1.end_id)
            c = next(node.position for node in nodes if node.id == e2.start_id)
            d = next(node.position for node in nodes if node.id == e2.end_id)
            inter = segment_intersection(a, b, c, d)
            if inter is not None:
                junctions.append({
                    'point': inter,
                    'edges': (e1.start_id, e1.end_id, e2.start_id, e2.end_id)
                })

    return edges, junctions

def connect_clusters(nodes: List[Node], edges: List[Edge]) -> List[Edge]:
    """
    Ensure full connectivity by checking for disconnected clusters.
    If multiple connected components exist, find the closest pair of nodes between
    different components and add an edge connecting them. Repeat until only one component remains.
    Returns a list of extra edges that were added.
    """
    extra_edges: List[Edge] = []

    # Build a graph from current edges using node IDs.
    G = nx.Graph()
    for node in nodes:
        G.add_node(node.id, pos=node.position)
    for edge in edges:
        G.add_edge(edge.start_id, edge.end_id)

    components = list(nx.connected_components(G))
    while len(components) > 1:
        min_dist = float('inf')
        best_pair = (None, None)
        # Consider every pair of components.
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                comp_i = components[i]
                comp_j = components[j]
                for id1 in comp_i:
                    pos1 = next(node.position for node in nodes if node.id == id1)
                    for id2 in comp_j:
                        pos2 = next(node.position for node in nodes if node.id == id2)
                        dist = np.linalg.norm(np.array(pos1) - np.array(pos2))
                        if dist < min_dist:
                            min_dist = dist
                            best_pair = (id1, id2)
        if best_pair[0] is not None and best_pair[1] is not None:
            new_edge = Edge(start_id=best_pair[0], end_id=best_pair[1])
            extra_edges.append(new_edge)
            G.add_edge(best_pair[0], best_pair[1])
            components = list(nx.connected_components(G))
        else:
            break
    return extra_edges

def save_graph_image(nodes: List[Dict], edges: List[Dict], image_filename: str = "dungeon_graph.png"):
    """
    Create a graph from nodes and edges, then save it as an image.
    Assumes each node is a dict with 'id' and 'key' (or 'id' if key missing),
    and each edge is a dict with 'start_id' and 'end_id'.
    """
    # Build a lookup from node id to room label (key)
    id_to_key = {}
    for node in nodes:
        label = node.get('key') or node.get('id', 'Unknown')
        id_to_key[node.get('id')] = label

    # Create the graph and add nodes using the room labels.
    G = nx.Graph()
    for node in nodes:
        label = id_to_key.get(node.get('id'))
        G.add_node(label)

    # Add edges, mapping start/end IDs to labels.
    for edge in edges:
        start_label = id_to_key.get(edge.get('start_id'), edge.get('start_id'))
        end_label = id_to_key.get(edge.get('end_id'), edge.get('end_id'))
        G.add_edge(start_label, end_label)

    # Draw the graph using a spring layout.
    pos = nx.spring_layout(G, seed=42)  # fixed seed for consistent layout
    plt.figure(figsize=(8, 6))
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color="lightblue",
        edge_color="gray",
        font_weight="bold",
        node_size=1500,
    )
    plt.title("Dungeon Layout")
    plt.savefig(image_filename)
    plt.close()

def generate_dungeon_map(*args, **kwargs) -> Dict[str, Any]:
    """
    Main map generation entry point with detailed logging.
    Accepts extra keyword arguments (like 'num_dice') and ignores them.
    """
    logger.info("🗺️ Starting dungeon map generation...")
    try:
        seed = random.randint(0, 100000)
        random.seed(seed)
        logger.info(f"🎲 Using fixed set of dice with seed {seed}")

        # Node generation using the fixed set.
        logger.info("🎯 Generating fixed set of nodes...")
        nodes = simulate_dice_drops()
        logger.info(f"📍 Created {len(nodes)} nodes (fixed set)")

        # Node processing.
        logger.info("🔄 Processing node clusters...")
        nodes = _process_nodes(nodes)
        logger.info(f"🏘️ Final node count after processing: {len(nodes)}")

        # Edge creation: form loops and connect free nodes.
        logger.info("🔗 Creating loops and connecting free nodes...")
        edges, junctions = create_loops_and_connect(nodes)
        logger.info(f"🛣️ Created {len(edges)} connections with {len(junctions)} junctions")

        # Ensure full connectivity by bridging disconnected clusters.
        extra_edges = connect_clusters(nodes, edges)
        if extra_edges:
            edges.extend(extra_edges)
            logger.info(f"🔗 Added {len(extra_edges)} extra edge(s) to connect clusters.")

        logger.info("✅ Map generation completed successfully")
        return {
            "content": "Dungeon Map Details",
            "metadata": {
                "nodes": [asdict(n) for n in nodes],
                "edges": [asdict(e) for e in edges],
                "junctions": junctions,
                "seed": seed,
                "stats": {
                    "total_rooms": len(nodes),
                    "connections": len(edges),
                    "entrances": sum(1 for n in nodes if n.is_entrance)
                }
            }
        }
    except Exception as e:
        logger.error(f"❌ Map generation failed: {str(e)}")
        return {"error": str(e)}

"""STL analysis and geometry detection utilities"""

import numpy as np
import trimesh
from pathlib import Path
from typing import Tuple, List, Optional
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import tempfile


def find_battery_gap(mesh: trimesh.Trimesh) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find the battery cover gap in the bottom case.
    Returns the bounds of the gap region.
    """
    # The battery gap is typically a rectangular opening in the back plate
    # We'll analyze the bottom face (minimum Z) to find discontinuities
    
    vertices = mesh.vertices
    faces = mesh.faces
    
    # Find the minimum Z value (bottom of the case)
    z_min = vertices[:, 2].min()
    z_threshold = z_min + 2.0  # Look within 2mm of the bottom
    
    # Get vertices near the bottom
    bottom_vertices_mask = vertices[:, 2] <= z_threshold
    bottom_vertex_indices = np.where(bottom_vertices_mask)[0]
    
    if len(bottom_vertex_indices) == 0:
        return None, None
    
    # Get the bounding box of bottom vertices
    bottom_verts = vertices[bottom_vertex_indices]
    bounds_min = bottom_verts.min(axis=0)
    bounds_max = bottom_verts.max(axis=0)
    
    # The gap is likely in the middle region
    # We'll look for a region with missing vertices
    x_center = (bounds_min[0] + bounds_max[0]) / 2
    y_center = (bounds_min[1] + bounds_max[1]) / 2
    
    # Define a search region for the gap (typically central)
    gap_search_width = (bounds_max[0] - bounds_min[0]) * 0.6
    gap_search_height = (bounds_max[1] - bounds_min[1]) * 0.6
    
    gap_min = np.array([
        x_center - gap_search_width/2,
        y_center - gap_search_height/2,
        z_min
    ])
    
    gap_max = np.array([
        x_center + gap_search_width/2,
        y_center + gap_search_height/2,
        z_min + 5.0  # Gap extends up to 5mm
    ])
    
    return gap_min, gap_max


def analyze_magsafe_ring(mesh: trimesh.Trimesh) -> dict:
    """
    Analyze the magsafe ring reference model to extract dimensions.
    """
    vertices = mesh.vertices
    
    # Find the circular recess by analyzing the geometry
    # The ring is typically a circular depression
    
    # Get bounds
    bounds_min = vertices.min(axis=0)
    bounds_max = vertices.max(axis=0)
    
    # The ring is likely centered in X-Y
    center_x = (bounds_min[0] + bounds_max[0]) / 2
    center_y = (bounds_min[1] + bounds_max[1]) / 2
    
    # Find vertices that form a circle
    # We'll look for vertices at a consistent radius from center
    xy_vertices = vertices[:, :2]
    center_xy = np.array([center_x, center_y])
    
    distances = np.linalg.norm(xy_vertices - center_xy, axis=1)
    
    # Find the most common radius (within tolerance)
    # This is likely the ring radius
    hist, bins = np.histogram(distances, bins=50)
    
    # Find peaks in the histogram (likely ring boundaries)
    peak_indices = np.where(hist > np.percentile(hist, 75))[0]
    
    if len(peak_indices) > 0:
        # Get the outer radius
        outer_radius_idx = peak_indices[-1]
        outer_radius = (bins[outer_radius_idx] + bins[outer_radius_idx + 1]) / 2
        
        # Inner radius is typically about 60-70% of outer for magsafe
        inner_radius = outer_radius * 0.65
        
        # Depth is the Z difference
        depth = bounds_max[2] - bounds_min[2]
        
        return {
            "center": [center_x, center_y],
            "outer_radius": outer_radius,
            "inner_radius": inner_radius,
            "depth": min(depth, 3.0),  # Typical magsafe depth is ~2-3mm
        }
    
    # Fallback to standard magsafe dimensions if detection fails
    return {
        "center": [center_x, center_y],
        "outer_radius": 28.0,  # Standard magsafe outer diameter ~56mm
        "inner_radius": 18.0,  # Standard magsafe inner diameter ~36mm  
        "depth": 2.5,  # Standard depth
    }


def visualize_modifications(original_mesh: trimesh.Trimesh, 
                          gap_bounds: Tuple[np.ndarray, np.ndarray],
                          magsafe_info: dict,
                          output_path: Optional[Path] = None) -> Path:
    """
    Visualize planned modifications on the mesh.
    """
    fig = plt.figure(figsize=(12, 6))
    
    # Original mesh - bottom view
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')
    vertices = original_mesh.vertices
    faces = original_mesh.faces
    
    ax1.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2],
                    triangles=faces, alpha=0.3, shade=True,
                    edgecolor='black', linewidth=0.1)
    
    ax1.view_init(elev=-90, azim=0)
    ax1.set_title("Original (Bottom View)")
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    ax1.set_zlabel('Z')
    
    # Planned modifications - 2D view
    ax2 = fig.add_subplot(1, 2, 2)
    
    # Plot mesh outline
    bounds = original_mesh.bounds
    rect = plt.Rectangle((bounds[0][0], bounds[0][1]), 
                         bounds[1][0] - bounds[0][0],
                         bounds[1][1] - bounds[0][1],
                         fill=False, edgecolor='black', linewidth=2)
    ax2.add_patch(rect)
    
    # Show battery gap to be filled
    if gap_bounds[0] is not None:
        gap_rect = plt.Rectangle((gap_bounds[0][0], gap_bounds[0][1]),
                                gap_bounds[1][0] - gap_bounds[0][0],
                                gap_bounds[1][1] - gap_bounds[0][1],
                                fill=True, facecolor='red', alpha=0.3,
                                edgecolor='red', linewidth=2)
        ax2.add_patch(gap_rect)
        ax2.text(gap_bounds[0][0], gap_bounds[0][1] - 5, 
                "Battery gap (to fill)", color='red')
    
    # Show magsafe ring location
    if magsafe_info:
        center = magsafe_info["center"]
        outer_circle = Circle(center, magsafe_info["outer_radius"],
                             fill=False, edgecolor='blue', linewidth=2)
        inner_circle = Circle(center, magsafe_info["inner_radius"],
                            fill=False, edgecolor='blue', linewidth=1,
                            linestyle='--')
        ax2.add_patch(outer_circle)
        ax2.add_patch(inner_circle)
        ax2.text(center[0], center[1] - magsafe_info["outer_radius"] - 5,
                f"Magsafe ring (depth: {magsafe_info['depth']:.1f}mm)",
                color='blue', ha='center')
    
    ax2.set_xlim(bounds[0][0] - 10, bounds[1][0] + 10)
    ax2.set_ylim(bounds[0][1] - 10, bounds[1][1] + 10)
    ax2.set_aspect('equal')
    ax2.set_title("Planned Modifications (Top View)")
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Y (mm)')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix='.png'))
    
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path
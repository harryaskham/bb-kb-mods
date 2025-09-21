"""STL file manipulation utilities"""

import numpy as np
import trimesh
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image
import io
import tempfile
from typing import Tuple, Optional


def load_stl(filepath: Path) -> trimesh.Trimesh:
    """Load an STL file into a trimesh object"""
    mesh = trimesh.load_mesh(str(filepath))
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = mesh.dump(concatenate=True)
    return mesh


def save_stl(mesh: trimesh.Trimesh, filepath: Path):
    """Save a trimesh object to an STL file"""
    mesh.export(str(filepath))


def render_mesh_views(mesh: trimesh.Trimesh, output_path: Optional[Path] = None) -> Path:
    """Render mesh from multiple viewpoints and save as image"""
    fig = plt.figure(figsize=(16, 12))
    
    views = [
        ("Top", [0, 0, 1], [0, 1, 0]),
        ("Bottom", [0, 0, -1], [0, 1, 0]),
        ("Front", [0, -1, 0], [0, 0, 1]),
        ("Back", [0, 1, 0], [0, 0, 1]),
        ("Left", [-1, 0, 0], [0, 0, 1]),
        ("Right", [1, 0, 0], [0, 0, 1]),
    ]
    
    for idx, (title, camera_pos, up_vec) in enumerate(views):
        ax = fig.add_subplot(2, 3, idx + 1, projection='3d')
        
        # Plot the mesh vertices
        vertices = mesh.vertices
        faces = mesh.faces
        
        # Create a simple wireframe plot
        ax.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2],
                       triangles=faces, alpha=0.3, shade=True, 
                       edgecolor='black', linewidth=0.1)
        
        # Set view angle
        if title == "Top":
            ax.view_init(elev=90, azim=0)
        elif title == "Bottom":
            ax.view_init(elev=-90, azim=0)
        elif title == "Front":
            ax.view_init(elev=0, azim=0)
        elif title == "Back":
            ax.view_init(elev=0, azim=180)
        elif title == "Left":
            ax.view_init(elev=0, azim=-90)
        elif title == "Right":
            ax.view_init(elev=0, azim=90)
        
        ax.set_title(title)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        
        # Equal aspect ratio
        ax.set_box_aspect([1,1,1])
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix='.png'))
    
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path


def get_mesh_info(mesh: trimesh.Trimesh) -> dict:
    """Get basic information about a mesh"""
    bounds = mesh.bounds
    center = mesh.centroid
    
    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "bounds_min": bounds[0].tolist(),
        "bounds_max": bounds[1].tolist(),
        "size": (bounds[1] - bounds[0]).tolist(),
        "center": center.tolist(),
        "volume": mesh.volume,
        "is_watertight": mesh.is_watertight,
        "is_valid": mesh.is_watertight,  # Use is_watertight as proxy for validity
    }


def analyze_z_layers(mesh: trimesh.Trimesh, z_height: float, thickness: float = 0.5) -> trimesh.path.Path2D:
    """Get a cross-section of the mesh at a specific Z height"""
    # Create a plane at the specified Z height
    plane_origin = [0, 0, z_height]
    plane_normal = [0, 0, 1]
    
    # Get the cross-section
    section = mesh.section(plane_origin=plane_origin, plane_normal=plane_normal)
    
    if section is None:
        return None
    
    # Convert to 2D path
    path_2d = section.to_planar()[0]
    return path_2d
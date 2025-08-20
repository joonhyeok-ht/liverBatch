import sys
import os
# import torch
# from torch.autograd import Variable
import numpy as np
import math
# from sklearn.decomposition import PCA

# import gen_utils as gu
# from sklearn.neighbors import KDTree
# from scipy.spatial import KDTree
import open3d as o3d

# from torch.utils.tensorboard import SummaryWriter


class COpen3DMesh :
    @staticmethod
    def create_coordinate_frame(coord : np.ndarray, size = 1) :
        coordTmp = coord.reshape(3).tolist()
        originFrame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=size, origin=coordTmp)
        return originFrame
    @staticmethod
    def create_point_cloud(point : np.ndarray) :
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(point)
        return pcd
    @staticmethod
    def create_triangle_mesh(vertex : np.ndarray, index : np.ndarray) -> o3d.geometry.TriangleMesh :
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(vertex)
        mesh.triangles = o3d.utility.Vector3iVector(index)
        return mesh
    @staticmethod
    def create_line(vertex : np.ndarray, index : np.ndarray) -> o3d.geometry.LineSet :
        line_set = o3d.geometry.LineSet(
            points=o3d.utility.Vector3dVector(vertex), 
            lines=o3d.utility.Vector2iVector(index),
            )
        return line_set
    
    @staticmethod
    def create_aabb(point : np.ndarray) -> o3d.geometry.AxisAlignedBoundingBox :
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(point)
        aabb = pcd.get_axis_aligned_bounding_box()
        return aabb
    @staticmethod
    def create_obb(point : np.ndarray) -> o3d.geometry.OrientedBoundingBox :
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(point)
        obb = pcd.get_oriented_bounding_box()
        return obb
    @staticmethod
    def create_sphere(pos : np.ndarray, radius : float, resolution = 30) -> o3d.geometry.TriangleMesh :
        posTmp = pos.reshape(3)
        sphere = o3d.geometry.TriangleMesh.create_sphere(radius=radius, resolution=resolution)
        sphere.translate(translation=posTmp)
        return sphere
    
    @staticmethod
    def load_triangle_mesh(fullPath : str) -> o3d.geometry.TriangleMesh :
        if os.path.exists(fullPath) == False :
            return None
        
        mesh = o3d.io.read_triangle_mesh(fullPath)
        # mesh = COpen3DMesh.triangle_mesh_remove_duplicated_vertex(mesh)
        return mesh
    @staticmethod
    def save_triangle_mesh(fullPath : str, mesh : o3d.geometry.TriangleMesh) :
        o3d.io.write_triangle_mesh(fullPath, mesh)


    @staticmethod
    def render_pcd_list(listPCD : list, title = "", origin = False, originSize = 1, normal = False) :
        if len(listPCD) == 0 :
            return
        
        if origin == True :
            originFrame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=originSize, origin=[0, 0, 0])
            listPCD.append(originFrame)
        o3d.visualization.draw_geometries(listPCD, window_name = title, point_show_normal=normal)
    @staticmethod
    def save_pcd_list(fullPngPath : str, listPCD : list, title = "", origin = False, originSize = 1) :
        if len(listPCD) == 0 :
            return
        
        if origin == True :
            originFrame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=originSize, origin=[0, 0, 0])
            listPCD.append(originFrame)

        vis = o3d.visualization.Visualizer()
        vis.create_window(visible=False)

        for pcd in listPCD :
            vis.add_geometry(pcd)
            vis.update_geometry(pcd)

        vis.poll_events()
        vis.update_renderer()
        vis.capture_screen_image(fullPngPath)
        vis.destroy_window()
    
    
    # point cloud 
    def point_cloud_set_color(pcd : o3d.geometry.PointCloud, color : np.ndarray) :
        pcd.colors = o3d.utility.Vector3dVector(color)
    def point_cloud_set_uniform_color(pcd : o3d.geometry.PointCloud, color : np.ndarray) :
        uniformColorTmp = color.reshape(3).tolist()
        pcd.paint_uniform_color(uniformColorTmp)
    def point_cloud_set_normal(pcd : o3d.geometry.PointCloud, normal : np.ndarray) :
        pcd.normals = o3d.utility.Vector3dVector(normal)
    

    # triangle mesh
    def triangle_mesh_set_color(mesh : o3d.geometry.TriangleMesh, color : np.ndarray) :
        mesh.colors = o3d.utility.Vector3dVector(color)
    def triangle_mesh_set_uniform_color(mesh : o3d.geometry.TriangleMesh, color : np.ndarray) :
        colorTmp = color.reshape(3).tolist()
        mesh.paint_uniform_color(colorTmp)
    def triangle_mesh_set_normal(mesh : o3d.geometry.TriangleMesh, normal : np.ndarray) :
        mesh.normals = o3d.utility.Vector3dVector(normal)
    def triangle_mesh_get_vertex(mesh : o3d.geometry.TriangleMesh) -> np.ndarray :
        return np.array(mesh.vertices, dtype=np.float32)
    def triangle_mesh_get_index(mesh : o3d.geometry.TriangleMesh) -> np.ndarray :
        return np.array(mesh.triangles, dtype=np.uint32)
    def triangle_mesh_get_normal(mesh : o3d.geometry.TriangleMesh) -> np.ndarray :
        return np.array(mesh.vertex_normals, dtype=np.float32)


    # line
    def line_set_color(line : o3d.geometry.LineSet, color :np.ndarray) :
        line.colors =  o3d.utility.Vector3dVector(color)
    def line_set_uniform_color(line : o3d.geometry.LineSet, color : np.ndarray) :
        uniformColorTmp = color.reshape(3).tolist()
        colors = [uniformColorTmp for _ in range(len(line.lines))]
        line.colors = o3d.utility.Vector3dVector(colors)


    # aabb
    @staticmethod
    def aabb_set_color(aabb : o3d.geometry.AxisAlignedBoundingBox, color : np.ndarray) :
        colorTmp = color.reshape(3).tolist()
        aabb.color = colorTmp
    @staticmethod
    def aabb_get_min(aabb : o3d.geometry.AxisAlignedBoundingBox) -> np.ndarray :
        return np.array(aabb.get_min_bound()).reshape(-1, 3).astype(np.float32)
    @staticmethod
    def aabb_get_max(aabb : o3d.geometry.AxisAlignedBoundingBox) -> np.ndarray :
        return np.array(aabb.get_max_bound()).reshape(-1, 3).astype(np.float32)
    @staticmethod
    def aabb_get_half_size(aabb : o3d.geometry.AxisAlignedBoundingBox) -> np.ndarray :
        maxBound = aabb.get_max_bound()
        minBound = aabb.get_min_bound()
        return np.array(maxBound - minBound).reshape(-1, 3).astype(np.float32) / 2.0


    # obb
    @staticmethod
    def obb_set_color(obb : o3d.geometry.OrientedBoundingBox, color : np.ndarray) :
        colorTmp = color.reshape(3).tolist()
        obb.color = colorTmp
    @staticmethod
    def obb_get_half_size(obb : o3d.geometry.OrientedBoundingBox) -> np.ndarray:
        return obb.extent.reshape(-1, 3).astype(np.float32) / 2.0
    @staticmethod
    def obb_get_center(obb : o3d.geometry.OrientedBoundingBox) -> np.ndarray:
        return obb.center.reshape(-1, 3).astype(np.float32)
    @staticmethod
    def obb_get_axis(obb : o3d.geometry.OrientedBoundingBox) -> np.ndarray :
        return obb.R.astype(np.float32)
    

    # algorithm
    @staticmethod
    def triangle_mesh_remove_duplicated_vertex(mesh : o3d.geometry.TriangleMesh) :
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()
        mesh.remove_degenerate_triangles()
        mesh.compute_vertex_normals()
        return mesh
    
    
    def __init__(self) -> None:
        pass









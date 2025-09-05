
'''
File : blenderArrangeObjects.py
Version : 2025_04_07
'''
import bpy
import os
import sys

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)

def add_new_collection(collection_name:str) :

    collection = bpy.data.collections.get(collection_name)
    if collection :
        print(f" '{collection_name}' already exists.")
    else :    
        new_collection = bpy.data.collections.new(name=collection_name)

        # Scene Collection에 새로운 Collection 추가
        bpy.context.scene.collection.children.link(new_collection)

def is_collection_child(parent_name, child_name):
    parent = bpy.data.collections.get(parent_name)
    if not parent:
        print(f"Not Found Collection : '{parent_name}'")
        return False

    # 자식들 중에 이름이 일치하는 것이 있는지 확인
    return any(child.name == child_name for child in parent.children)

def is_object_in_collection(collection_name, object_name):
    collection = bpy.data.collections.get(collection_name)
    obj = bpy.data.objects.get(object_name)

    if not collection:
        print(f"Not Found Collection '{collection_name}'")
        return False
    if not obj:
        print(f"Not Found Object'{object_name}'")
        return False

    return obj.name in collection.objects

def get_collections_of_object(obj):
    return [col.name for col in bpy.data.collections if obj.name in col.objects]

def move_collection_to_collection(child_name, parent_name) :
    child = bpy.data.collections.get(child_name)
    parent = bpy.data.collections.get(parent_name)
    
    if not is_collection_child(parent_name, child_name) :
        parent.children.link(child)
        bpy.context.scene.collection.children.unlink(child)
        
        print(f"{child_name} has been moved under {parent_name}.")
    else :
        print(f"{child_name} is already under {parent_name}. Skip")

def remove_collection(collection_name) :
    
    # Collection 찾기
    collection = bpy.data.collections.get(collection_name)

    # Collection 삭제
    if collection:
        bpy.data.collections.remove(collection)
        print(f"'{collection_name}' Collection has been removed.")
    else:
        print(f"'The collection named {collection_name} cannot be found.")

def arrange_objects_for_lung() :
    
    main_collection = bpy.data.collections.get("Collection")
    vessels = ["Artery_L", "Artery_R", "Bronchus_L", "Bronchus_R", "Vein_L", "Vein_R"]
    if main_collection :        
        # for obj in main_collection.objects :
        for obj in bpy.data.objects :
            nn = obj.name
            token = nn.split('_')
            tokenCnt = len(token)
            dst_collection_name = ""
            if "RA" in nn or "RB" in nn or "RV" in nn or "LA" in nn or "LB" in nn or "LV" in nn :
                dst_collection_name = f"Vessel{nn[0]}"
            elif "Lung_RS" in nn or "Lung_LS" in nn :
                if tokenCnt == 4 : #segment
                    dst_collection_name = f"Segment{token[2]}"
                elif tokenCnt == 5 : #subsegment
                    dst_collection_name = f"Subsegment{token[3]}"
            elif "Bone_Rib_" in nn :
                dst_collection_name = "Rib"
            elif nn in vessels :
                dst_collection_name = f"Vessel{nn[0]}"
            else :
                dst_collection_name = "Others"   
                         
            if dst_collection_name != "":        
                dst_collection = bpy.data.collections.get(dst_collection_name)
                curr_parent_collection_names = get_collections_of_object(obj)
                src_parent_collection = bpy.data.collections.get(curr_parent_collection_names[0])
                if dst_collection :
                    if not is_object_in_collection(dst_collection_name, obj.name) :
                        dst_collection.objects.link(obj)
                        src_parent_collection.objects.unlink(obj)     
                     
def proc_arrange_lung_objects() :       
    add_new_collection("Artery")
    add_new_collection("Bronchus")
    add_new_collection("Vein")
    add_new_collection("Others")
    
    add_new_collection("SegmentA")
    add_new_collection("SubsegmentA")
    add_new_collection("VesselA")
    move_collection_to_collection("SegmentA", "Artery")
    move_collection_to_collection("SubsegmentA", "Artery")
    move_collection_to_collection("VesselA", "Artery")    
    
    add_new_collection("SegmentB")
    add_new_collection("SubsegmentB")
    add_new_collection("VesselB")
    move_collection_to_collection("SegmentB", "Bronchus")
    move_collection_to_collection("SubsegmentB", "Bronchus")
    move_collection_to_collection("VesselB", "Bronchus")
    
    add_new_collection("SegmentV")
    add_new_collection("SubsegmentV")
    add_new_collection("VesselV")
    move_collection_to_collection("SegmentV", "Vein")
    move_collection_to_collection("SubsegmentV", "Vein")
    move_collection_to_collection("VesselV", "Vein")
    
    add_new_collection("Rib")
    move_collection_to_collection("Rib", "Others")
   
    arrange_objects_for_lung()
    remove_collection("Collection")

if __name__ == "__main__" : 
    proc_arrange_lung_objects()
import torch
import torch.nn.functional as F
import torchvision.transforms as T
from .config import cfg

import os
import glob
import shutil
import numpy as np
from PIL import Image


def load_and_preprocess_image(file_path):
    """
    Load and preprocess image.
    """
    img = Image.open(file_path).convert("RGB")

    image_transforms = T.Compose([
        T.Resize(cfg.INPUT.SIZE_TEST), 
        T.ToTensor(), 
        T.Normalize(mean = cfg.INPUT.PIXEL_MEAN, std = cfg.INPUT.PIXEL_STD)
    ])                                 # define transformations

    img = image_transforms(img)        # apply transformations
    img = img.unsqueeze(0)             # add batch dimension (i.e., [1, 3, 256, 128])
    return img


def compute_distances(model, query_image, gallery_images, query_path, gallery_paths, is_duplicate, device):
    """
    Compute the distances between the query image and the gallery images.
    """
    list_of_dist = []
    query_embedding = model(query_image.to(device))[2]    # forward pass to get the embedding of the query image

    # Calculate the similarity and distance.
    for index in range(len(gallery_images)):
        gallery_embedding = model(gallery_images[index].to(device))[2]
        similarity = F.cosine_similarity(query_embedding, gallery_embedding)
        dist = 1 - similarity
        list_of_dist.append(dist.cpu().detach().numpy()[0])
    
    list_of_dist = np.array(list_of_dist)

    if is_duplicate:
        list_of_dist[np.argmin(list_of_dist)] = list_of_dist[np.argmax(list_of_dist)]

    return list_of_dist


def process_dist_mat(dist_mat):
    """
    Process the distance matrix to count the number of individuals.
    """
    output_dict = dict()
    number_of_images = len(dist_mat)
    keys = [-1] * number_of_images
    counter = 0
    for r in range(len(dist_mat)):
        row = dist_mat[r]
        matched_index = np.argmin(row)
        # print(f"Image Index: {r}")
        # print(f"Distance: {row}")
        # print(f"Matched Image Index: {matched_index}")
        
        if keys[r] == -1 and keys[matched_index] == -1:
            output_dict[counter] = [r]
            keys[r] = counter
            output_dict[keys[r]].append(matched_index)
            keys[matched_index] = counter
            counter += 1
            
        elif keys[r] == -1 and keys[matched_index] != -1:
            output_dict[keys[matched_index]].append(r)
            keys[r] = keys[matched_index]
        
        elif keys[r] != -1 and keys[matched_index] == -1:
            output_dict[keys[r]].append(matched_index)
            keys[matched_index] = keys[r]
        # print(f"Output: {output_dict}\n")
        
    # print(keys)
    return output_dict


def format_output_dict(image_paths, output_dict):
    """
    Format the output dictionary with image filenames.
    """
    image_names = []
    output_dict_with_filenames = dict()
    for img_path in image_paths:
        img_name = img_path.split("/")[-1]
        image_names.append(img_name)
    
    for id, list_of_imgs in output_dict.items():
        id = "ID-" + str(id)
        list_of_img_names = []
        for img in list_of_imgs:
            list_of_img_names.append(image_names[img])
        if id not in output_dict_with_filenames:
            output_dict_with_filenames[id] = list_of_img_names
    
    return output_dict_with_filenames


def show_results(q_img_paths, reid_dict):
    """
    Show and save the re-identification results.
    """
    print(f"The CARE model successfully identified {len(reid_dict)} individuals in the dataset.")
    print("\nRe-identification Result:")
    print(reid_dict)
    print("-" * 30)
    print()
    
    # Save same individuals to one directory.
    for id, list_of_imgs in reid_dict.items():
        id_dir = os.path.join("./Reid_results", id)
        if not os.path.exists(id_dir):
            os.makedirs(id_dir)
            print(f"Directory '{id_dir}' is created.")
        for img in list_of_imgs:
            img_dir = os.path.join("./Stoat/query", img)
            id_img_dir = os.path.join(id_dir, img)
            shutil.copyfile(img_dir, id_img_dir)
            print(f"  - Image '{img}' is appended to '{id_dir}'")
        print()




def main(image_path_list, progress_callback=None):
    DEVICE = "cpu"
    cfg_file_path = "vit_care.yml"
    saved_model_path = "CARE_Traced.pt"
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'detection_model', 'CARE_Traced.pt'))
    vit_care_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'detection_model', 'vit_care.yml'))

    # Read and import the cfg file.
    cfg.merge_from_file(vit_care_path)
    cfg.merge_from_list([])
    cfg.freeze()

    # Load the traced model (CARE).
    CARE_Model = torch.jit.load(model_path)
    CARE_Model = CARE_Model.to(DEVICE)
    CARE_Model.eval()    # set the model in evaluation mode

    '''
    # Construct the directories to images.
    query_root_dir = "Stoat/query"
    query_image_paths = sorted(glob.glob(os.path.join(query_root_dir, "*.jpg")))
    gallery_root_dir = "Stoat/gallery"
    gallery_image_paths = sorted(glob.glob(os.path.join(gallery_root_dir, "*.jpg")))
    '''

    # Load and preprocess all query images.
    query_images = []
    for q_img_path in image_path_list:
        query_images.append(load_and_preprocess_image(q_img_path))
    print("-" * 30)
    print(f"Number of Query Images: {len(query_images)}")
    
    # Load and preprocess all gallery images.
    gallery_images = []
    for g_img_path in image_path_list:
        gallery_images.append(load_and_preprocess_image(g_img_path))
    print(f"Number of Gallery Images: {len(gallery_images)}\n")
    
    distance_mat = []    # a distance matrix
    # Compute the similarity of each matched image pair.
    for index in range(len(image_path_list)):
        dist = compute_distances(model = CARE_Model, 
                                 query_image = query_images[index], 
                                 gallery_images = gallery_images, 
                                 query_path = image_path_list[index],
                                 gallery_paths = image_path_list,
                                 is_duplicate = True,    # check whether the query image has a duplicate in Gallery
                                 device = DEVICE)
        distance_mat.append(dist)

        progress = int((index + 1) / len(image_path_list) * 100)
        if progress_callback:
            progress_callback(progress)

    id_dict = process_dist_mat(distance_mat)
    output_dict = format_output_dict(image_path_list, id_dict)
    return output_dict
    #show_results(image_path_list, output_dict)



#main()
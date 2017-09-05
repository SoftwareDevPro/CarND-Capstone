"""
Simple script that analyzes model accuracy at traffic lights prediction for various levels of cropping.
Crops are centered on image center
"""

import os
import glob
import pprint

import keras
import cv2
import tqdm
import numpy as np



def get_images_as_path(path):

    paths = sorted(glob.glob(os.path.join(path, "*.jpg")))
    return [cv2.imread(path) for path in paths]


def get_model(model_path, weight_path):

    with open(model_path, 'r') as f:
        loaded_model_json = f.read()

    model = keras.models.model_from_json(loaded_model_json)
    model.load_weights(weight_path)
    # self.graph = tf.get_default_graph()

    return model


def process_image(image):

    desired_shape = (128, 128)
    image = cv2.resize(image, desired_shape, cv2.INTER_LINEAR)
    image = image.astype('float32') / 255
    processed_image = image.reshape(1, *image.shape)

    return processed_image


def crop_image(image, margin):
    """
    Crops margin number of pixels on each side
    :param image: numpy arrray
    :param margin: int
    :return: numpy array
    """

    y_size = image.shape[0]
    x_size = image.shape[1]

    return image[margin:y_size - margin, margin:x_size - margin]


def get_predictions_accuracy(model, images, class_id, margin):

    cropped_images = [crop_image(image, margin) for image in images]
    processed_images = [process_image(image) for image in cropped_images]

    predicted_ids = []

    for image in processed_images:

        predicted_class_id = model.predict_classes(image, batch_size=1, verbose=0)
        predicted_ids.append(predicted_class_id[0])

    # cv2.imshow("image", cropped_images[0])
    # cv2.waitKey(0)

    accuracy = np.mean(np.array(predicted_ids) == class_id)
    return accuracy


def main():

    model_dir = "/home/student/CarND-Capstone/ros/src/tl_detector/light_classification/saved_models/"
    model_path = os.path.join(model_dir, "model128.json")
    weight_path = os.path.join(model_dir, "weights128.hdf5")

    model = get_model(model_path, weight_path)

    # data_dir = "/home/student/data_partition/data/bag_dump_loop_with_traffic_light/"
    data_dir = "/home/student/data_partition/data/bag_dump_just_traffic_light/"

    green_images = get_images_as_path(os.path.join(data_dir, "green"))
    red_images = get_images_as_path(os.path.join(data_dir, "red"))

    green_accuracies = []
    red_accuracies = []

    margins = list(range(0, 500, 50))

    for margin in tqdm.tqdm(margins):

        green_accuracy = get_predictions_accuracy(model, green_images, class_id=2, margin=margin)
        green_accuracies.append((margin, green_accuracy))

        red_accuracy = get_predictions_accuracy(model, red_images, class_id=0, margin=margin)
        red_accuracies.append((margin, red_accuracy))

    green_accuracies = sorted(green_accuracies, key=lambda x: x[1], reverse=True)
    red_accuracies = sorted(red_accuracies, key=lambda x: x[1], reverse=True)

    print("For data: {}".format(os.path.dirname(data_dir)))
    print("Sorted green accuracies: {}".format(green_accuracies))
    print("Sorted red accuracies: {}".format(red_accuracies))


if __name__ == "__main__":

    main()

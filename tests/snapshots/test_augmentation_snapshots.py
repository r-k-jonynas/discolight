import shutil
import os
import filecmp
import random
import pytest
import yamale
import numpy as np
from discolight.annotations import (annotations_to_numpy_array,
                                    annotations_from_numpy_array)
from discolight.augmentations.augmentation.types import ColorAugmentation
from discolight.writers.image.directory import Directory as DirectoryWriter
from discolight.writers.annotation.fourcornerscsv import (FourCornersCSV as
                                                          FourCornersCSVWriter)
from discolight.disco import disco
from discolight.util.image import save_image
import discolight.augmentations.factory as factory

augmentations_factory = factory.make_augmentations_factory()


@pytest.fixture(params=list(factory.get_augmentations_set().values()))
def augmentation_name_params(request):

    options = {}

    try:
        with open("./fixtures/{}.yml".format(
                request.param.__name__)) as aug_options_yml:

            options = yamale.make_data(
                content=aug_options_yml.read())[0][0]["options"]
    except IOError:
        pass

    return request.param.__name__, options


@pytest.fixture
def augmentation(augmentation_name_params):

    name, params = augmentation_name_params

    return augmentations_factory(name, **params)


@pytest.mark.usefixtures("sample_image")
def test_augmentation(augmentation, snapshot, tmp_path, sample_image):

    random.seed(1)
    img, annotations = sample_image

    bboxes = annotations_to_numpy_array(annotations)

    aug_img, aug_bboxes = augmentation.augment(img.copy(), bboxes.copy())

    if isinstance(augmentation, ColorAugmentation):

        assert np.array_equal(
            bboxes, aug_bboxes
        ), "{} is a ColorAugmentation, but it modified bboxes".format(
            augmentation.__name__)

    aug_annotations = annotations_from_numpy_array(aug_bboxes)

    with DirectoryWriter(
            directory=tmp_path,
            clean_directory=False) as image_writer, FourCornersCSVWriter(
                annotations_file=os.path.join(
                    tmp_path, "{}-bboxes".format(augmentation.__name__)),
                normalized=True) as annotation_writer:

        annotation_writer.write_annotations_for_image(
            "{}-image.jpg".format(augmentation.__name__), aug_img,
            aug_annotations)

        image_writer.write_image("{}-image.jpg".format(augmentation.__name__),
                                 aug_img)

    if snapshot["update_snapshots"]:

        if not os.path.isdir("./snapshots/augmentations"):
            os.mkdir("./snapshots/augmentations")

        shutil.copy(
            os.path.join(tmp_path, "{}-bboxes".format(augmentation.__name__)),
            "./snapshots/augmentations/{}-bboxes".format(
                augmentation.__name__))
        shutil.copy(
            os.path.join(tmp_path,
                         "{}-image.jpg".format(augmentation.__name__)),
            "./snapshots/augmentations/{}-image.jpg".format(
                augmentation.__name__))
        return

    assert filecmp.cmp(
        os.path.join(tmp_path, "{}-bboxes".format(augmentation.__name__)),
        "./snapshots/augmentations/{}-bboxes".format(augmentation.__name__)
    ), "Bounding boxes for {} do not match".format(augmentation.__name__)
    assert filecmp.cmp(
        os.path.join(tmp_path, "{}-image.jpg".format(augmentation.__name__)),
        "./snapshots/augmentations/{}-image.jpg".format(
            augmentation.__name__)), "Images for {} do not match".format(
                augmentation.__name__)


def test_disco_constructed_augmentation_same_as_factory_constructed(
        augmentation_name_params, snapshot, tmp_path, sample_image):

    random.seed(1)

    if snapshot["update_snapshots"]:
        raise RuntimeError(
            "This test must be run after snapshots are generated")

    name, params = augmentation_name_params

    aug = getattr(disco, name)(**params)

    img, annotations = sample_image

    aug_img, aug_annotations = aug(img, annotations)

    save_image(os.path.join(tmp_path, "aug_image.jpg"), aug_img)

    with FourCornersCSVWriter(os.path.join(tmp_path, "aug_annotations.csv"),
                              True) as annotations_writer:

        annotations_writer.write_annotations_for_image(
            "{}-image.jpg".format(name), aug_img, aug_annotations)

    assert filecmp.cmp(
        os.path.join(tmp_path, "aug_annotations.csv"),
        "./snapshots/augmentations/{}-bboxes".format(
            name)), "Bounding boxes for {} do not match".format(name)
    assert filecmp.cmp(os.path.join(tmp_path, "aug_image.jpg"),
                       "./snapshots/augmentations/{}-image.jpg".format(
                           name)), "Images for {} do not match".format(name)

from deeptracking.tracker.trackerbase import TrackerBase
from deeptracking.utils.transform import Transform
from deeptracking.data.dataset_utils import combine_view_transform, normalize_depth
from deeptracking.data.modelrenderer import ModelRenderer, InitOpenGL
from deeptracking.data.dataset_utils import normalize_scale, normalize_channels, unnormalize_label, image_blend
import PyTorchHelpers
import numpy as np
import os


class DeepTracker(TrackerBase):
    def __init__(self, camera, mean_std_path, object_width=0, model_3d_path="", model_3d_ao_path="", shader_path=""):
        self.image_size = None
        self.tracker_model = None
        self.translation_range = None
        self.rotation_range = None
        self.mean = None
        self.std = None
        self.debug_rgb = None
        self.debug_background = None
        self.camera = camera
        self.object_width = object_width

        # setup model
        model_class = PyTorchHelpers.load_lua_class("deeptracking/model/rgbd_tracker.lua", 'RGBDTracker')
        self.tracker_model = model_class('cuda')
        self.tracker_model.build_model()
        self.tracker_model.init_model()
        self.load_parameters_from_model_()
        self.load_mean_std_(mean_std_path)

        if model_3d_path != "" and model_3d_ao_path != "" and shader_path != "":
            self.setup_renderer(model_3d_path, model_3d_ao_path, shader_path)

        # setup buffers
        self.input_buffer = np.ndarray((1, 8, self.image_size[0], self.image_size[1]), dtype=np.float32)
        self.prior_buffer = np.ndarray((1, 7), dtype=np.float32)

    def setup_renderer(self, model_3d_path, model_3d_ao_path, shader_path):
        window = InitOpenGL(self.camera.width, self.camera.height)
        self.renderer = ModelRenderer(model_3d_path, shader_path, self.camera, window)
        self.renderer.load_ambiant_occlusion_map(model_3d_ao_path)

    def load(self, path):
        self.tracker_model.load(path)

    def print(self):
        self.tracker_model.show_model()

    def load_mean_std_(self, path):
        self.mean = np.load(os.path.join(path, "mean.npy"))
        self.std = np.load(os.path.join(path, "std.npy"))

    def load_parameters_from_model_(self):
        self.image_size = (int(self.tracker_model.get_configs("inputSize")), int(self.tracker_model.get_configs("inputSize")))
        self.translation_range = float(self.tracker_model.get_configs("translation_range"))
        self.rotation_range = float(self.tracker_model.get_configs("rotation_range"))

    def set_configs_(self, configs):
        self.tracker_model.set_configs(configs)

    def estimate_current_pose(self, previous_pose, current_rgb, current_depth):
        render_rgb, render_depth = self.renderer.render(previous_pose.inverse().transpose())
        #todo implement this part in gpu...
        rgbA, depthA = normalize_scale(render_rgb, render_depth, previous_pose, self.camera, self.image_size,
                                       self.object_width)
        rgbB, depthB = normalize_scale(current_rgb, current_depth, previous_pose, self.camera, self.image_size,
                                       self.object_width)

        depthA = normalize_depth(depthA, previous_pose.inverse())
        depthB = normalize_depth(depthB, previous_pose.inverse())

        rgbA, depthA = normalize_channels(rgbA, depthA, self.mean[:4], self.std[:4])
        rgbB, depthB = normalize_channels(rgbB, depthB, self.mean[4:], self.std[4:])
        self.input_buffer[0, 0:3, :, :] = rgbA
        self.input_buffer[0, 3, :, :] = depthA
        self.input_buffer[0, 4:7, :, :] = rgbB
        self.input_buffer[0, 7, :, :] = depthB
        self.prior_buffer[0] = np.array(previous_pose.to_parameters(isQuaternion=True))
        prediction = self.tracker_model.test([self.input_buffer, self.prior_buffer]).asNumpyTensor()
        prediction = unnormalize_label(prediction, self.translation_range, self.rotation_range)
        prediction = Transform.from_parameters(*prediction[0], is_degree=True)
        current_pose = combine_view_transform(previous_pose.inverse(), prediction).inverse()
        self.debug_rgb = render_rgb
        return current_pose

    def get_debug_screen(self, previous_frame):
        blend = image_blend(self.debug_rgb, previous_frame)
        return blend

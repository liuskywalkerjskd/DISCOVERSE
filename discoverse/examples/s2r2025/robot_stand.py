import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from discoverse.envs.mmk2_base import MMK2Base, MMK2Cfg
from judgement import TaskInfo, s2r2025_position_info, box_within_cabinet, prop_in_gripper, prop_within_table

cfg = MMK2Cfg()
cfg.mjcf_file_path = "mjcf/s2r2025_env.xml"
cfg.timestep       = 0.002
cfg.decimation     = 5
cfg.init_key = "pick"
cfg.sync     = True
cfg.headless = False
cfg.render_set = {
    "fps"    : 30,
    "width"  : 1920,
    "height" : 1080 
}
cfg.obj_list = [
    "box_carton" , "box_disk"    , "box_sheet"     ,
    "carton_01"  , "disk_01"     , "sheet_01"      ,
    "apple"      , "book"        , "cup"           ,
    "kettle"     , "scissors"    , "timeclock"     ,
    "wood"       , "xbox"        , "yellow_bowl"   ,
    "toy_cabinet", "cabinet_door", "cabinet_drawer",
]

cfg.gs_model_dict["background"]     = "scene/s2r2025/point_cloud_trans.ply"
cfg.gs_model_dict["box_carton"]     = "s2r2025/box.ply"
cfg.gs_model_dict["box_disk"]       = "s2r2025/box.ply"
cfg.gs_model_dict["box_sheet"]      = "s2r2025/box.ply"
cfg.gs_model_dict["carton_01"]      = "s2r2025/carton_01.ply"
cfg.gs_model_dict["disk_01"]        = "s2r2025/disk_01.ply"
cfg.gs_model_dict["sheet_01"]       = "s2r2025/sheet_01.ply"
cfg.gs_model_dict["apple"]          = "s2r2025/apple.ply"
cfg.gs_model_dict["book"]           = "s2r2025/book.ply"
cfg.gs_model_dict["cup"]            = "s2r2025/cup.ply"
cfg.gs_model_dict["kettle"]         = "s2r2025/kettle.ply"
cfg.gs_model_dict["scissors"]       = "s2r2025/scissors.ply"
cfg.gs_model_dict["timeclock"]      = "s2r2025/timeclock.ply"
cfg.gs_model_dict["wood"]           = "s2r2025/wood.ply"
cfg.gs_model_dict["xbox"]           = "s2r2025/xbox.ply"
cfg.gs_model_dict["yellow_bowl"]    = "s2r2025/yellow_bowl.ply"
cfg.gs_model_dict["toy_cabinet"]    = "s2r2025/toy_cabinet.ply"
cfg.gs_model_dict["cabinet_door"]   = "s2r2025/cabinet_door.ply"
cfg.gs_model_dict["cabinet_drawer"] = "s2r2025/cabinet_drawer.ply"

cfg.obs_rgb_cam_id   = None
cfg.obs_depth_cam_id = None
cfg.use_gaussian_renderer = False

# import rospy
# from discoverse.examples.ros1.mmk2_joy_ros1 import MMK2JOY
# class S2RNode(MMK2JOY):
class S2RNode(MMK2Base):
    gadgets_names = [
        "apple"     , "book" , "cup"  , "kettle"      , "scissors",
        "timeclock" , "wood" , "xbox" , "yellow_bowl" , "toy_cabinet"
    ]
    box_names = ["box_carton", "box_disk", "box_sheet"]
    props_names = ["carton_01", "disk_01", "sheet_01", "disk_02", "sheet_02"]

    def __init__(self, config):
        super().__init__(config)

        # self.options.frame = mujoco.mjtFrame.mjFRAME_SITE.value
        # self.options.flags[mujoco.mjtVisFlag.mjVIS_TRANSPARENT] = True
        # self.options.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = True
        self.round_id = self.config.round_id

    def post_load_mjcf(self):
        super().post_load_mjcf()
        self.gadgets_info = {}
        self.boxes_info = {}
        self.props_info = {}
        for n in self.gadgets_names:
            self.gadgets_info[n] = self.mj_model.jnt_qposadr[np.where(self.mj_model.jnt_bodyid == self.mj_data.body(n).id)[0]][0]
        for n in self.box_names:
            self.boxes_info[n] = self.mj_model.jnt_qposadr[np.where(self.mj_model.jnt_bodyid == self.mj_data.body(n).id)[0]][0]
        for n in self.props_names:
            self.props_info[n] = self.mj_model.jnt_qposadr[np.where(self.mj_model.jnt_bodyid == self.mj_data.body(n).id)[0]][0]

        self.taskInfos = {
            "round1" : TaskInfo(),
            "round2" : TaskInfo(),
            "round3" : TaskInfo(),
        }

    def reset(self):
        ret = super().reset()
        for k in self.taskInfos:
            self.taskInfos[k].reset()
            if int(k[-1]) < 3:
                del(self.taskInfos[k].scoring["d"])

        while True:
            self.gadgets_choice_ids = np.random.choice(np.arange(0, len(s2r2025_position_info["table"]["position"])), size=len(self.gadgets_names), replace=False)
            if "back" in s2r2025_position_info["table"]["info"][self.gadgets_choice_ids[self.gadgets_names.index("toy_cabinet")]].split(","):
                sel_R2_prop_id = np.random.randint(0, len(self.gadgets_names)-1) # no toy_cabinet
                sel_R3_prop_id = np.random.randint(0, len(self.gadgets_names)-1) # no toy_cabinet
                for i, (n, qid) in enumerate(self.gadgets_info.items()):
                    self.mj_data.qpos[qid:qid+3] = s2r2025_position_info["table"]["position"][self.gadgets_choice_ids[i]][0]
                    self.mj_data.qpos[qid+3:qid+7] = s2r2025_position_info["table"]["position"][self.gadgets_choice_ids[i]][1]
                    if i == sel_R2_prop_id:
                        infos = s2r2025_position_info["table"]["info"][self.gadgets_choice_ids[i]].split(",")
                        R2info_prop_name = np.random.choice(["carton", "disk", "sheet"], size=1)[0]
                        R2info_table_dir = np.random.choice(infos[1:], size=1)[0]
                        posi = self.mj_data.qpos[qid:qid+3].copy()
                        rmat = Rotation.from_quat(self.mj_data.qpos[qid+3:qid+7][[1,2,3,0]]).as_matrix()
                        if R2info_table_dir == "front":
                            posi -= 0.2 * rmat[:3,0]
                        elif R2info_table_dir == "back":
                            posi += 0.2 * rmat[:3,0]
                        elif R2info_table_dir == "left":
                            posi += 0.2 * rmat[:3,1]
                        elif R2info_table_dir == "right":
                            posi -= 0.2 * rmat[:3,1]
                        self.mj_model.site("site_round2_target").pos[:] = posi[:]
                        self.mj_model.site("site_round2_target").quat[:] = self.mj_data.qpos[qid+3:qid+7][:]
                        self.taskInfos["round2"].round = 2
                        self.taskInfos["round2"].instruction = f"Find the {R2info_prop_name} with a surface featuring robot textures, and put it to the {R2info_table_dir} of the {n}."
                        self.taskInfos["round2"].target_box_name = "box_" + R2info_prop_name
                        self.taskInfos["round2"].target_box_qpos_id = self.boxes_info[self.taskInfos["round2"].target_box_name]
                        self.taskInfos["round2"].target_prop_type = R2info_prop_name
                        self.taskInfos["round2"].target_prop_name = R2info_prop_name + "_01"
                        self.taskInfos["round2"].target_prop_qpos_id = self.props_info[self.taskInfos["round2"].target_prop_name]

                    if i == sel_R3_prop_id:
                        infos = s2r2025_position_info["table"]["info"][self.gadgets_choice_ids[i]].split(",")
                        props_toy = ["disk", "sheet"]
                        np.random.shuffle(props_toy)
                        draw_door_toy = ["drawer_top_layer", "drawer_bottom_layer"]
                        np.random.shuffle(draw_door_toy)
                        R3info_prop_name = props_toy[0]
                        R3info_drawer_layer = draw_door_toy[0]
                        R3info_table_dir = np.random.choice(infos[1:], size=1)[0]
                        posi = self.mj_data.qpos[qid:qid+3].copy()
                        rmat = Rotation.from_quat(self.mj_data.qpos[qid+3:qid+7][[1,2,3,0]]).as_matrix()
                        if R3info_table_dir == "front":
                            posi -= 0.2 * rmat[:3,0]
                        elif R3info_table_dir == "back":
                            posi += 0.2 * rmat[:3,0]
                        elif R3info_table_dir == "left":
                            posi += 0.2 * rmat[:3,1]
                        elif R3info_table_dir == "right":
                            posi -= 0.2 * rmat[:3,1]
                        self.mj_model.site("site_round3_target").pos[:] = posi[:]
                        self.mj_model.site("site_round3_target").quat[:] = self.mj_data.qpos[qid+3:qid+7][:]
                        self.taskInfos["round3"].round = 3
                        # Find another sheet as same as the one in the bowl, and put it in the drawer bottom-layer.
                        self.taskInfos["round3"].instruction = f"Find another prop as same as the one in the {R3info_drawer_layer.replace('_', ' ')}, and put it to the {R3info_table_dir} of the {n}."
                        self.taskInfos["round3"].target_box_name = "box_" + R3info_prop_name
                        self.taskInfos["round3"].target_box_qpos_id = self.boxes_info[self.taskInfos["round3"].target_box_name]
                        self.taskInfos["round3"].target_prop_type = R3info_prop_name
                        self.taskInfos["round3"].target_prop_name = R3info_prop_name + "_01"
                        self.taskInfos["round3"].target_prop_qpos_id = self.props_info[self.taskInfos["round3"].target_prop_name]
                        self.taskInfos["round3"].drawer_layer = R3info_drawer_layer.split("_")[1]

                    if n == "toy_cabinet":
                        rmat = Rotation.from_quat(self.mj_data.qpos[qid+3:qid+7][[1,2,3,0]]).as_matrix()
                        self.mj_data.qpos[qid:qid+3] += 0.15 * rmat[:3,0]
                tc_qid = self.gadgets_info["toy_cabinet"]
                if np.linalg.norm(self.mj_model.site("site_round2_target").pos[:] - self.mj_data.qpos[tc_qid:tc_qid+3]) > 0.3:
                    break

        mujoco.mj_forward(self.mj_model, self.mj_data)

        for p, d in zip(props_toy, draw_door_toy):
            self.mj_data.qpos[self.props_info[p+"_02"]:self.props_info[p+"_02"]+3] = self.mj_data.body(d).xpos[:]

        sel_R1_prop_id = np.random.randint(0, len(self.props_names))
        self.boxes_choice_ids = np.random.choice(np.arange(0, len(s2r2025_position_info["cabinet"]["position"])), size=len(self.box_names), replace=False)
        for i, (n, qid) in enumerate(self.boxes_info.items()):
            self.mj_data.qpos[qid:qid+3] = s2r2025_position_info["cabinet"]["position"][self.boxes_choice_ids[i]][0]
            self.mj_data.qpos[qid+3:qid+7] = s2r2025_position_info["cabinet"]["position"][self.boxes_choice_ids[i]][1]
            tmat_world2box = np.eye(4)
            tmat_world2box[:3, 3] = self.mj_data.qpos[qid:qid+3]
            tmat_world2box[:3, :3] = Rotation.from_quat(self.mj_data.qpos[qid+3:qid+7][[1,2,3,0]]).as_matrix()

            pos = s2r2025_position_info[n.split("_")[1]]["position"][np.random.randint(0, len(s2r2025_position_info[n.split("_")[1]]["position"]))]
            tmat_box2prop = np.eye(4)
            tmat_box2prop[:3, 3] = pos[0]
            tmat_box2prop[:3, :3] = Rotation.from_quat(np.array(pos[1])[[1,2,3,0]]).as_matrix()
            tmat_world2prop = tmat_world2box @ tmat_box2prop

            prop_qid = self.props_info[self.props_names[i]]
            self.mj_data.qpos[prop_qid:prop_qid+3] = tmat_world2prop[:3, 3]
            self.mj_data.qpos[prop_qid+3:prop_qid+7] = Rotation.from_matrix(tmat_world2prop[:3, :3]).as_quat()[[3,0,1,2]]
            if i == sel_R1_prop_id:
                infos = s2r2025_position_info["cabinet"]["info"][self.boxes_choice_ids[i]].split(",")
                R1info_prop_name = n.split("_")[1] # ["carton", "disk", "sheet"]
                R1info_floor_idx = infos[1].split("_")[0]   # ["second", "third", "fourth"]
                R1info_cabinet_dir = infos[0].split("_")[0] # ["left", "right"]
                R1info_table_dir = np.random.choice(["left", "right"], size=1)[0]
                self.taskInfos["round1"].round = 1
                self.taskInfos["round1"].instruction = f"Take the {R1info_prop_name} from the {R1info_floor_idx} floor of the {R1info_cabinet_dir} cabinet, and put it on the {R1info_table_dir} table."
                self.taskInfos["round1"].target_box_name = "box_" + R1info_prop_name
                self.taskInfos["round1"].target_box_qpos_id = self.boxes_info[self.taskInfos["round1"].target_box_name]
                self.taskInfos["round1"].target_prop_type = R1info_prop_name
                self.taskInfos["round1"].target_prop_name = R1info_prop_name + "_01"
                self.taskInfos["round1"].target_prop_qpos_id = self.props_info[self.taskInfos["round1"].target_prop_name]
                self.taskInfos["round1"].table_direction = R1info_table_dir

        print('-' * 100)
        r = f"round{self.round_id}"
        tif = self.taskInfos[r]
        print(f"{r} : {tif.instruction}")
        print(f"    target_box_name : {tif.target_box_name}")
        print(f"    target_prop_name : {tif.target_prop_name}")
        return ret

    def printMessage(self):
        ret = super().printMessage()
        r = f"round{self.round_id}"
        tinfo = self.taskInfos[r]
        print(f"{r} : {tinfo.instruction}")
        print(f"    target_box_name  : {tinfo.target_box_name}")
        print(f"    target_prop_name : {tinfo.target_prop_name}")
        print(f"    scoring : {tinfo.scoring}")
        return ret

    def cv2WindowKeyPressCallback(self, key):
        ret = super().cv2WindowKeyPressCallback(key)
        if key == ord("c"):
            print(np.array2string(self.mj_data.contact.geom, separator=',', suppress_small=True))
            
            round_str = f"round{self.round_id}"
            prop_name = self.taskInfos[round_str].target_prop_name

            for bd in [prop_name, "lft_finger_left_link", "lft_finger_right_link", "rgt_finger_left_link", "rgt_finger_right_link"]:
                bd_gemo_id_range = (self.mj_model.body(bd).geomadr[0], self.mj_model.body(bd).geomadr[0]+self.mj_model.body(bd).geomnum[0])
                print(bd, bd_gemo_id_range)

            print(self.check_contact(prop_name, "lft_finger_right_link"), self.check_contact(prop_name, "lft_finger_left_link"))
            print(self.check_contact(prop_name, "rgt_finger_right_link"), self.check_contact(prop_name, "rgt_finger_left_link"))

        return ret

    def check_contact(self, body1, body2):
        body1_gemo_id_range = (self.mj_model.body(body1).geomadr[0], self.mj_model.body(body1).geomadr[0]+self.mj_model.body(body1).geomnum[0])
        body2_gemo_id_range = (self.mj_model.body(body2).geomadr[0], self.mj_model.body(body2).geomadr[0]+self.mj_model.body(body2).geomnum[0])
        b1r = body1_gemo_id_range if body1_gemo_id_range[0] < body2_gemo_id_range[0] else body2_gemo_id_range
        b2r = body2_gemo_id_range if body1_gemo_id_range[0] < body2_gemo_id_range[0] else body1_gemo_id_range

        for i in range(self.mj_data.ncon):
            geom_id = sorted(self.mj_data.contact.geom[i].tolist())
            if b1r[0] <= geom_id[0] < b1r[1] and b2r[0] <= geom_id[1] < b2r[1]:
                return True
        return False

    def post_physics_step(self):
        round_str = f"round{self.round_id}"

        box_posi = self.mj_data.qpos[self.taskInfos[round_str].target_box_qpos_id:self.taskInfos[round_str].target_box_qpos_id+3]
        # box_quat = self.mj_data.qpos[self.taskInfos[round_str].target_box_qpos_id+3:self.taskInfos[round_str].target_box_qpos_id+7]
        box_name = self.taskInfos[round_str].target_box_name

        prop_posi = self.mj_data.qpos[self.taskInfos[round_str].target_prop_qpos_id:self.taskInfos[round_str].target_prop_qpos_id+3]
        # prop_quat = self.mj_data.qpos[self.taskInfos[round_str].target_prop_qpos_id+3:self.taskInfos[round_str].target_prop_qpos_id+7]
        prop_name = self.taskInfos[round_str].target_prop_name

        if self.round_id == 1:
            if not self.taskInfos[round_str].scoring["a"] and not box_within_cabinet(box_posi):
                if (self.check_contact(box_name, "lft_finger_right_link") or self.check_contact(box_name, "lft_finger_left_link")) and \
                    (self.check_contact(box_name, "rgt_finger_right_link") or self.check_contact(box_name, "rgt_finger_left_link")):
                    self.taskInfos[round_str].scoring["a"] = True
                    print(f">>> {round_str} scoring : 'a' done\n", self.taskInfos[round_str].scoring)

            if not self.taskInfos[round_str].scoring["b"]:
                if prop_in_gripper(self.mj_data.body("lft_finger_left_link").xpos, self.mj_data.body("lft_finger_right_link").xpos, prop_posi, self.taskInfos[round_str].target_prop_type) \
                    or prop_in_gripper(self.mj_data.body("rgt_finger_left_link").xpos, self.mj_data.body("rgt_finger_right_link").xpos, prop_posi, self.taskInfos[round_str].target_prop_type):
                    if (self.check_contact(prop_name, "lft_finger_right_link") and self.check_contact(prop_name, "lft_finger_left_link")) \
                        or (self.check_contact(prop_name, "rgt_finger_right_link") and self.check_contact(prop_name, "rgt_finger_left_link")):
                        self.taskInfos[round_str].scoring["b"] = True
                        print(f">>> {round_str} scoring : 'b' done\n", self.taskInfos[round_str].scoring)

            if self.taskInfos[round_str].scoring["a"] and self.taskInfos[round_str].scoring["b"] and not self.taskInfos[round_str].scoring["c"]:
                if (not self.check_contact(prop_name, "lft_finger_right_link")) and (not self.check_contact(prop_name, "lft_finger_left_link")) and \
                    (not self.check_contact(prop_name, "rgt_finger_right_link")) and (not self.check_contact(prop_name, "rgt_finger_left_link")):
                    if prop_within_table(prop_posi, self.taskInfos[round_str].table_direction) and self.check_contact(prop_name, self.taskInfos[round_str].table_direction+"_table") and prop_posi[2] > 0.75:
                        self.taskInfos[round_str].scoring["c"] = True
                        print(f">>> {round_str} scoring : 'c' done\n", self.taskInfos[round_str].scoring)

        elif self.round_id == 2:
            if not self.taskInfos[round_str].scoring["a"] and not box_within_cabinet(box_posi):
                if (self.check_contact(box_name, "lft_finger_right_link") or self.check_contact(box_name, "lft_finger_left_link")) and \
                    (self.check_contact(box_name, "rgt_finger_right_link") or self.check_contact(box_name, "rgt_finger_left_link")):
                    self.taskInfos[round_str].scoring["a"] = True
                    print(f">>> {round_str} scoring : 'a' done\n", self.taskInfos[round_str].scoring)

            if not self.taskInfos[round_str].scoring["b"]:
                if prop_in_gripper(self.mj_data.body("lft_finger_left_link").xpos, self.mj_data.body("lft_finger_right_link").xpos, prop_posi, self.taskInfos[round_str].target_prop_type) \
                    or prop_in_gripper(self.mj_data.body("rgt_finger_left_link").xpos, self.mj_data.body("rgt_finger_right_link").xpos, prop_posi, self.taskInfos[round_str].target_prop_type):
                    if (self.check_contact(prop_name, "lft_finger_right_link") and self.check_contact(prop_name, "lft_finger_left_link")) \
                        or (self.check_contact(prop_name, "rgt_finger_right_link") and self.check_contact(prop_name, "rgt_finger_left_link")):
                        self.taskInfos[round_str].scoring["b"] = True
                        print(f">>> {round_str} scoring : 'b' done\n", self.taskInfos[round_str].scoring)

            if not self.taskInfos[round_str].scoring["c"] and self.taskInfos[round_str].scoring["a"] and self.taskInfos[round_str].scoring["b"]:
                if (not self.check_contact(prop_name, "lft_finger_right_link")) and (not self.check_contact(prop_name, "lft_finger_left_link")) and \
                    (not self.check_contact(prop_name, "rgt_finger_right_link")) and (not self.check_contact(prop_name, "rgt_finger_left_link")):
                    if ((prop_within_table(prop_posi, "left") and self.check_contact(prop_name, "left_table")) or \
                        (prop_within_table(prop_posi, "right") and self.check_contact(prop_name, "right_table"))) and \
                        np.linalg.norm(prop_posi - self.mj_model.site("site_round2_target").pos) < 0.1:
                        self.taskInfos[round_str].scoring["c"] = True
                        print(f">>> {round_str} scoring : 'c' done\n", self.taskInfos[round_str].scoring)

        elif self.round_id == 3:
            if not self.taskInfos[round_str].scoring["a"] and not box_within_cabinet(box_posi):
                if (self.check_contact(box_name, "lft_finger_right_link") or self.check_contact(box_name, "lft_finger_left_link")) and \
                    (self.check_contact(box_name, "rgt_finger_right_link") or self.check_contact(box_name, "rgt_finger_left_link")):
                    self.taskInfos[round_str].scoring["a"] = True
                    print(f">>> {round_str} scoring : 'a' done\n", self.taskInfos[round_str].scoring)

            if not self.taskInfos[round_str].scoring["b"]:
                if prop_in_gripper(self.mj_data.body("lft_finger_left_link").xpos, self.mj_data.body("lft_finger_right_link").xpos, prop_posi, self.taskInfos[round_str].target_prop_type) \
                    or prop_in_gripper(self.mj_data.body("rgt_finger_left_link").xpos, self.mj_data.body("rgt_finger_right_link").xpos, prop_posi, self.taskInfos[round_str].target_prop_type):
                    if (self.check_contact(prop_name, "lft_finger_right_link") and self.check_contact(prop_name, "lft_finger_left_link")) \
                        or (self.check_contact(prop_name, "rgt_finger_right_link") and self.check_contact(prop_name, "rgt_finger_left_link")):
                        self.taskInfos[round_str].scoring["b"] = True
                        print(f">>> {round_str} scoring : 'b' done\n", self.taskInfos[round_str].scoring)

            if not self.taskInfos[round_str].scoring["c"] and self.taskInfos[round_str].scoring["a"] and self.taskInfos[round_str].scoring["b"]:
                if (not self.check_contact(prop_name, "lft_finger_right_link")) and (not self.check_contact(prop_name, "lft_finger_left_link")) and \
                    (not self.check_contact(prop_name, "rgt_finger_right_link")) and (not self.check_contact(prop_name, "rgt_finger_left_link")):
                    if ((prop_within_table(prop_posi, "left") and self.check_contact(prop_name, "left_table")) or \
                        (prop_within_table(prop_posi, "right") and self.check_contact(prop_name, "right_table"))) and \
                        np.linalg.norm(prop_posi - self.mj_model.site("site_round3_target").pos) < 0.1:
                        self.taskInfos[round_str].scoring["c"] = True
                        print(f">>> {round_str} scoring : 'c' done\n", self.taskInfos[round_str].scoring)
            
            if not self.taskInfos[round_str].scoring["d"]:
                if (self.taskInfos[round_str].drawer_layer == "top" and self.mj_data.qpos[self.mj_model.joint("jcb_door").qposadr[0]] > np.pi/4.) or \
                    (self.taskInfos[round_str].drawer_layer == "bottom" and self.mj_data.qpos[self.mj_model.joint("jcb_drawer").qposadr[0]] > 0.05):
                    self.taskInfos[round_str].scoring["d"] = True
                    print(f">>> {round_str} scoring : 'd' done\n", self.taskInfos[round_str].scoring)

        else:
            raise ValueError(f"Invalid round_id : {self.round_id}")

if __name__ == "__main__":
    np.set_printoptions(precision=3, suppress=True, linewidth=200)
    np.random.seed(0)

    # rospy.init_node('mmk2_mujoco_node', anonymous=True)

    cfg.init_key = "pick"
    cfg.round_id = 3
    sim_node = S2RNode(cfg)
    obs = sim_node.reset()
    action = sim_node.init_joint_ctrl.copy()

    while sim_node.running:
        sim_node.teleopProcess()
        obs, _, _, _, _ = sim_node.step(sim_node.target_control)
        # obs, _, _, _, _ = sim_node.step(action)

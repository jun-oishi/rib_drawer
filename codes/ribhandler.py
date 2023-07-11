# coding:utf-8

"""翼リブ図面を描画するためのモジュール."""

import airfoilhandler
import dxfdrawer
import numpy as np
from scipy import interpolate
import csv
import os

NUM_POINTS_TO_DRAW_OUTLINE = 200


class _Stringer:
    """
    ストリンガーの諸元を管理するクラス.

    T字に組んだものを想定して外形の接線方向を向くものをtan、
    外形に垂直なものをnormとする
    位置はx座標の翼弦に対する比で表して下面の場合は負とする

    Attributes
    ----------
    __tan_thickness : float
    __tan_width : float
    __norm_thickness : float
    __norm_width : float
    __position : float
        ストリンガー代表位置(中央)のx座標の翼弦に対する比(0~1)
        下面の場合は位置を-1倍して与える
    """

    def __init__(
        self,
        tan_thickness: float,
        tan_width: float,
        norm_thickness: float,
        norm_width: float,
        position: float,
    ):
        """ストリンガの厚み等をセットする."""
        self.__tan_thickness = tan_thickness
        self.__tan_width = tan_width
        self.__norm_thickness = norm_thickness
        self.__norm_width = norm_width
        self.__position = position
        return

    def get_hole_nodes(self, chord, rib_outline):
        """
        ストリンガ穴描画用の点を取得する.

        ストリンガはT字に組んだものを想定して凸字形の穴を描く
        """
        is_upper = np.sign(self.__position)
        stringer_x_abs = chord * np.abs(self.__position)
        # 点列を取得する(常に左から右の順)
        if is_upper == 1:
            points = rib_outline.get_points("upper")[::-1, :]
        else:
            points = rib_outline.get_points("lower")

        left_point = points[points[:, 0] < stringer_x_abs][-1]
        right_point = points[points[:, 0] > stringer_x_abs][0]
        sandwiching_points = np.array([left_point, right_point])
        pinned_point = np.array(
            [
                stringer_x_abs,
                np.interp(
                    stringer_x_abs, sandwiching_points[:, 0], sandwiching_points[:, 1]
                ),
            ]
        )
        theta = np.arctan2(
            right_point[1] - left_point[1], right_point[0] - left_point[0]
        )

        hole_nodes = pinned_point.reshape((1, 2))
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes, dxfdrawer.direct(self.__tan_width / 2, theta + np.pi)
        )
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes,
            dxfdrawer.direct(self.__tan_thickness, theta - is_upper * np.pi / 2),
        )
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes,
            dxfdrawer.direct((self.__tan_width - self.__norm_thickness) / 2, theta),
        )
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes,
            dxfdrawer.direct(self.__norm_width, theta - is_upper * np.pi / 2),
        )
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes, dxfdrawer.direct(self.__norm_thickness, theta)
        )
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes,
            dxfdrawer.direct(self.__norm_width, theta + is_upper * np.pi / 2),
        )
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes,
            dxfdrawer.direct((self.__tan_width - self.__norm_thickness) / 2, theta),
        )
        hole_nodes = dxfdrawer.append_next_point(
            hole_nodes,
            dxfdrawer.direct(self.__tan_thickness, theta + is_upper * np.pi / 2),
        )
        return hole_nodes[1:]


class _RearSpar:
    """リアスパ穴の描画に関わる変数をまとめるクラス.

    Attributes
    ----------
    diameter : float
        リアスパの直径[mm]
    dist : float
        リアスパと主桁の中心間距離[mm]
    theta : float
        主副桁中心を結ぶ線分と翼弦線のなす角[rad]
    """

    def __init__(self, diameter: float, dist: float, theta: float):
        """
        リアスパ位置をまとめる.

        Parameters
        ----------
        diameter : float
        dist_from_mainspar : float
            リアスパと主桁の中心間距離
        direction : float
            主副桁中心を結ぶ線分と翼弦線のなす角[deg]
            翼弦に並行真後ろ向きを0として下向きを正とする(符号を入れ替えて保存する)
        """
        self.__diameter = diameter
        self.__dist = dist
        self.__theta = -np.deg2rad(theta)
        return

    @property
    def diameter(self) -> float:
        return self.__diameter

    @property
    def dist(self) -> float:
        return self.__dist

    @property
    def theta(self) -> float:
        """[rad]"""
        return self.__theta


class Rib:
    """1枚のリブを表現するクラス.

    Attributes
    ----------
    __rib_name : str
        リブの名前 (ファイル名にもなる)
    __airfoil_name0 : str
        翼型の名前
    __airfoil_name1 : str | None
        翼型の名前(混合する場合)
    __mix_ratio : float
    __chord : float
        翼弦長[mm]
    __aoa : float
        迎角[deg]
    __plank_thickness : float
        上面、前縁プランクの厚み[mm]
    __ribcap_thickness : float
        リブキャップの厚み[mm]
    __upper_plank_end_x : float
        上面プランク下端のx座標(chordに対する比)
    __lower_plank_end_x : float
        下面プランク下端のx座標(chordに対する比)
    __stringers : list of _Stringer
    __beam_hole_x : float
        桁穴位置のx座標(chordに対する比)
    __beam_diameter : float
        桁穴径[mm]
    __rearspar : _RearSpar
    __bracing_hole_pos : float
        ブレーシング穴位置のx座標(主桁-リアスパ間の距離に対する比)
    """

    def __init__(
        self,
        rib_name: str,
        airfoil_name0: str,
        airfoil_name1: str,
        mix_ratio: float,
        chord: float,
        aoa: float,
        plank_thickness: float,
        ribcap_thickness: float,
        upper_plank_end_x: float,
        lower_plank_end_x: float,
        stringers: list[_Stringer],
        beam_hole_x: float,
        beam_diameter: float,
        rearspar: _RearSpar,
        bracing_hole_pos: float,
    ):
        """
        初期化メソッド.

        引数多いから気をつけて
        """
        self.__name: str = rib_name
        self.__airfoil_name0 = airfoil_name0
        if (airfoil_name1 is None) or (airfoil_name1 == ""):
            self.__airfoil_name1 = None
        else:
            self.__airfoil_name1 = airfoil_name1
        self.__mix_ratio = mix_ratio
        self.__chord = chord
        self.__aoa = aoa

        self.__plank_thickness = plank_thickness
        self.__ribcap_thickness = ribcap_thickness
        self.__upper_plank_end_x = upper_plank_end_x
        self.__lower_plank_end_x = lower_plank_end_x

        self.__stringers = stringers

        self.__beam_hole_x = beam_hole_x
        self.__beam_diameter = beam_diameter

        self.__rearspar = rearspar
        self.__bracing_hole_pos = bracing_hole_pos
        return

    @property
    def airfoil_name0(self) -> str:
        return self.__airfoil_name0

    @property
    def airfoil_name1(self) -> str | None:
        return self.__airfoil_name1

    def draw(self, save_directory, airfoils):
        """
        リブを描画する.

        Parameters
        ----------
        save_directory : string
            描画したdxfファイルを保存するディレクトリの(相対)パス
        airfoils : dict of Airfoil
            描画に必要な翼型の辞書
        """
        if self.__airfoil_name1 is not None:
            airfoil = airfoilhandler.mix(
                airfoils[self.__airfoil_name0],
                airfoils[self.__airfoil_name1],
                self.__mix_ratio,
            )
        else:
            airfoil = airfoils[self.__airfoil_name0]

        self.__file = dxfdrawer.newfile(save_directory + self.__name + ".dxf")
        self.__draw_airfoil_outline(airfoil)
        self.__draw_rib_outline()
        self.__draw_stringer_holes()
        self.__draw_main_beam_hole()
        self.__write_ribname()
        self.__draw_rearspar_hole()
        self.__draw_bracing_holes()
        self.__file.save()
        return True

    def __draw_airfoil_outline(self, airfoil):
        """
        翼外形を描画する.

        リブ外形描画の際に再利用するため
        描画した点列を wing_outline として Airfoil インスタンスで保存する
        """
        raw_points = airfoil.get_points()
        idx_sep_points = [
            np.argmax(raw_points[:, 1]),  # y座標最大の点
            np.argmin(raw_points[:, 1]),  # y座標最小の点
        ]
        raw_sections = [
            raw_points[: idx_sep_points[0] + 1, :],
            raw_points[idx_sep_points[0] : idx_sep_points[1] + 1, :],
            raw_points[idx_sep_points[1] :, :],
        ]

        # 前縁をはさむ区間はxyを入れ替えて補間する
        interpolated_points = np.array([]).reshape((0, 2))
        for i, raw_section in enumerate(raw_sections):
            if i == 0:
                # 1区間目(上面後部)は反転させてxが増加列になるように
                x = raw_section[::-1, 0]
                y = raw_section[::-1, 1]
            elif i == 1:
                # 2区間目(前縁付近)はxyを入れ替える
                x = raw_section[::-1, 1]
                y = raw_section[::-1, 0]
            else:
                # 3区間目(下面後部)は素直
                x = raw_section[:, 0]
                y = raw_section[:, 1]
            pchip = interpolate.PchipInterpolator(x, y)
            qx = np.linspace(x[0], x[-1], NUM_POINTS_TO_DRAW_OUTLINE)
            qy = pchip(qx)
            if i == 0:
                interpolated_section = np.array([qx[::-1], qy[::-1]]).T
            elif i == 1:
                interpolated_section = np.array([qy[::-1], qx[::-1]]).T
            else:
                interpolated_section = np.array([qx, qy]).T
            # 最後の点は重複するので落として追加
            interpolated_points = np.concatenate(
                [interpolated_points, interpolated_section[:-1]]
            )

        # 各区間の最後は落としているので後縁を追加
        interpolated_points = np.concatenate([interpolated_points, [[1, 0]]])
        scaled = interpolated_points * self.__chord

        self.__file.polyline(scaled)
        chordline = np.array([[0, 0], scaled[0]])
        self.__file.polyline(chordline)

        self.wing_outline = airfoilhandler.Airfoil(points=scaled)

        return True

    def __draw_rib_outline(self):
        """
        リブの外形(翼型をプランク/リブキャップ分オフセットしたもの)を描画する.

        wing_outline を利用するので __draw_airfoil_outline の後の実行する
        ストリンガ穴、桁穴描画のために
        描画した点を rib_outline として Airfoil インスタンスで保存する
        """
        plank_thickness = self.__plank_thickness
        ribcap_thickness = self.__ribcap_thickness

        upper_plank_end_x_abs = self.__chord * self.__upper_plank_end_x
        upper_points = self.wing_outline.get_points("upper")
        upper_plank_end_idx = np.sum(upper_points > upper_plank_end_x_abs)
        upper_capped = upper_points[: upper_plank_end_idx + 1]
        upper_capped = dxfdrawer.offset(upper_capped, ribcap_thickness)

        lower_plank_end_x_abs = self.__chord * self.__lower_plank_end_x
        lower_points = self.wing_outline.get_points("lower")
        lower_plank_end_idx = -int(np.sum(lower_points > lower_plank_end_x_abs))
        lower_capped = lower_points[lower_plank_end_idx - 1 :]
        lower_capped = dxfdrawer.offset(lower_capped, ribcap_thickness)

        front_points = self.wing_outline.get_points("all")[
            upper_plank_end_idx:lower_plank_end_idx
        ]
        front_planked = dxfdrawer.offset(front_points, plank_thickness)

        rib_outline = np.concatenate([upper_capped, front_planked, lower_capped])

        # TODO: 後縁付近を線形補間で上手いことやって閉じたポリラインにしたい

        self.__file.polyline(rib_outline)

        self.rib_outline = airfoilhandler.Airfoil(points=rib_outline)

        return True

    def __draw_stringer_holes(self):
        """ストリンガの穴を描く."""
        for stringer in self.__stringers:
            self.__file.polyline(
                stringer.get_hole_nodes(self.__chord, self.rib_outline)
            )

        return True

    def __draw_main_beam_hole(self):
        """
        桁穴を描画する.

        リアスパ穴の描画等で使うため桁穴中心座標を __beam_hole_center として保存する
        """
        center_x_abs = self.__beam_hole_x * self.__chord
        upper_points = self.rib_outline.get_points("upper")
        upper_y = np.interp(center_x_abs, upper_points[::-1, 0], upper_points[::-1, 1])
        lower_points = self.rib_outline.get_points("lower")
        lower_y = np.interp(center_x_abs, lower_points[:, 0], lower_points[:, 1])

        center_y = (upper_y + lower_y) / 2

        beam_hole_center = np.array([center_x_abs, center_y])
        self.__beam_hole_center = beam_hole_center
        self.__file.circle(beam_hole_center, self.__beam_diameter / 2)

        # 水平線、垂直線を描く
        aoa = np.deg2rad(self.__aoa)
        left_point = self.__beam_hole_center + dxfdrawer.direct(
            self.__chord * self.__beam_hole_x * 1.2, aoa + np.pi
        )
        right_point = left_point + dxfdrawer.direct(self.__chord * 1.2, aoa)
        self.__file.polyline([left_point, right_point])

        thickness = upper_y - lower_y
        upper_point = self.__beam_hole_center + dxfdrawer.direct(
            thickness, aoa + np.pi / 2
        )
        lower_point = self.__beam_hole_center + dxfdrawer.direct(
            thickness, aoa - np.pi / 2
        )
        self.__file.polyline([upper_point, lower_point])

        return True

    def __write_ribname(self):
        self.__file.text(self.__name, self.__beam_hole_center, self.__aoa)

    def __draw_rearspar_hole(self):
        """
        リアスパ穴を描画する.

        主桁穴の位置を利用するので __draw_main_beam_hole の後に実行する
        ブレーシングの穴の描画で使うため中心の座標を rearspar_hole_center として保存する
        """
        rearspar = self.__rearspar
        center = self.__beam_hole_center + dxfdrawer.direct(
            rearspar.dist, np.deg2rad(rearspar.theta)
        )
        self.__file.circle(center, rearspar.diameter / 2)
        self.rearspar_hole_center = center

        # 中心マーク
        aoa = np.deg2rad(self.__aoa)
        left_point = center + dxfdrawer.direct(rearspar.diameter, aoa + np.pi)
        right_point = center + dxfdrawer.direct(rearspar.diameter, aoa)
        self.__file.polyline([left_point, right_point])

        upper_point = center + dxfdrawer.direct(rearspar.diameter, aoa + np.pi / 2)
        lower_point = center + dxfdrawer.direct(rearspar.diameter, aoa - np.pi / 2)
        self.__file.polyline([upper_point, lower_point])

        return True

    def __draw_bracing_holes(self):
        """ブレーシングワイヤの穴を描画する."""
        beam_ctr = self.__beam_hole_center
        rearspar_ctr = self.rearspar_hole_center

        bracing_hole_pos = self.__bracing_hole_pos
        centers = [
            dxfdrawer.divide([beam_ctr, rearspar_ctr], bracing_hole_pos),
            dxfdrawer.divide([beam_ctr, rearspar_ctr], 1 - bracing_hole_pos),
        ]
        if bracing_hole_pos == 0.5:
            centers = centers[:1]

        for center in centers:
            self.__file.circle(center, self.__rearspar.diameter / 2)

        return True


class RibCollection:
    """リブの集まりを扱うクラス."""

    def load_config(self, config_dir: str, config_filename: str):
        """設定ファイルを読み込む."""
        path = os.path.join(config_dir, config_filename)
        with open(path, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            values = [line[2] for line in reader]

        self.__ribdata_filename = values[0]
        self.__plank_thickness = float(values[1])
        self.__ribcap_thickness = float(values[2])
        self.__tan_stringer_thickness = float(values[3])
        self.__tan_stringer_width = float(values[4])
        self.__norm_stringer_thickness = float(values[5])
        self.__norm_stringer_width = float(values[6])

        self.__load_ribdata(config_dir)

    def __load_ribdata(self, dir_name: str):
        """"""
        path = os.path.join(dir_name, self.__ribdata_filename)
        with open(path, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            table = [row for row in reader]
            table = [
                {
                    "rib_name": row[0],
                    "airfoil0": row[1],
                    "airfoil1": row[2],
                    "mix_ratio": float(row[3]),
                    "chord": float(row[4]),
                    "aoa": float(row[5]),
                    "beam_hole_x": float(row[6]),
                    "beam_diameter": float(row[7]),
                    "rearspar": {
                        "dist": float(row[8]),
                        "angle": float(row[9]),
                        "diameter": float(row[10]),
                    },
                    "upper_plank_end_x": float(row[11]),
                    "lower_plank_end_x": float(row[12]),
                    "bracing_hole_pos": float(row[13]),
                    "stringer_positions": [float(val) for val in row[14:]],
                }
                for row in table[2:]
            ]
        self.__set_ribdata(table)

    def __set_ribdata(self, table):
        ribs = []
        for row in table:
            rearspar = _RearSpar(
                row["rearspar"]["diameter"],
                row["rearspar"]["dist"],
                row["rearspar"]["angle"],
            )
            stringers = [
                _Stringer(
                    tan_thickness=self.__tan_stringer_thickness,
                    tan_width=self.__tan_stringer_width,
                    norm_thickness=self.__norm_stringer_thickness,
                    norm_width=self.__norm_stringer_width,
                    position=stringer_position,
                )
                for stringer_position in row["stringer_positions"]
            ]
            ribs.append(
                Rib(
                    rib_name=row["rib_name"],
                    airfoil_name0=row["airfoil0"],
                    airfoil_name1=row["airfoil1"],
                    mix_ratio=row["mix_ratio"],
                    chord=row["chord"],
                    aoa=row["aoa"],
                    beam_hole_x=row["beam_hole_x"],
                    beam_diameter=row["beam_diameter"],
                    rearspar=rearspar,
                    stringers=stringers,
                    upper_plank_end_x=row["upper_plank_end_x"],
                    lower_plank_end_x=row["lower_plank_end_x"],
                    bracing_hole_pos=row["bracing_hole_pos"],
                    plank_thickness=self.__plank_thickness,
                    ribcap_thickness=self.__ribcap_thickness,
                )
            )
        self.__ribs = ribs

    def read_unique_airfoils(self, dir_path):
        """必要な翼型のdatファイルを読み込む."""
        airfoil_names = []
        for rib in self.__ribs:
            if rib.airfoil_name0 not in airfoil_names:
                airfoil_names.append(rib.airfoil_name0)
            if rib.airfoil_name1 is not None and (
                rib.airfoil_name1 not in airfoil_names
            ):
                airfoil_names.append(rib.airfoil_name1)

        airfoils = {}
        for airfoil_name in airfoil_names:
            filepath = dir_path + airfoil_name + ".dat"
            airfoils[airfoil_name] = airfoilhandler.Airfoil(filepath=filepath)

        self.airfoils = airfoils

        return True

    def draw_each(self, save_directory):
        """
        それぞれのリブを書いて保存する.

        Attributes
        ----------
        save_directory : string
            ファイルを保存するフォルダのパス
            '/'で終わる形
        """
        for rib in self.__ribs:
            rib.draw(save_directory, self.airfoils)
        return

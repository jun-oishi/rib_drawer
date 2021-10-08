# coding:utf-8

"""翼リブ図面自動描画プログラムの本体."""

import ribhandler
import csv
import os

DATA_DIRECTORY = os.path.dirname(__file__) + '/../data/'
AIRFOIL_DIRECTORY = DATA_DIRECTORY + 'airfoils/'
SAVE_DIRECTORY = DATA_DIRECTORY + 'figure/'
CONFIG_DIRECTORY = DATA_DIRECTORY + 'config/'


class Config:
    """設定ファイルを扱うためのクラス."""

    def __init__(self, config_file_path):
        """設定ファイルを読み込む."""
        with open(config_file_path, 'r') as file:
            reader = csv.reader(file)
            values = [line[2] for line in reader]

        self.rib_file_path = CONFIG_DIRECTORY + values[0]
        self.dat_directory = AIRFOIL_DIRECTORY
        self.save_directory = SAVE_DIRECTORY
        self.plank_thickness = float(values[1])
        self.ribcap_thickness = float(values[2])
        self.tan_stringer_thickness = float(values[3])
        self.tan_stringer_width = float(values[4])
        self.norm_stringer_thickness = float(values[5])
        self.norm_stringer_width = float(values[6])
        return

    def read_rib_specs(self):
        """self.rib_file_path からリブの諸元を読み込む."""
        with open(self.rib_file_path, mode='r') as file:
            reader = csv.reader(file)
            table = [row for row in reader]
            table = [
                {
                    'rib_name': row[0],
                    'airfoil0': row[1],
                    'airfoil1': row[2],
                    'mix_ratio': float(row[3]),
                    'chord': float(row[4]),
                    'aoa': float(row[5]),
                    'beam_hole_x': float(row[6]),
                    'beam_diameter': float(row[7]),
                    'rearspar': {
                        'dist': float(row[8]),
                        'angle': float(row[9]),
                        'diameter': float(row[10])
                    },
                    'upper_plank_end_x': float(row[11]),
                    'lower_plank_end_x': float(row[12]),
                    'bracing_hole_pos': float(row[13]),
                    'stringer_positions': [float(val) for val in row[14:]]
                }
                for row in table[2:]
            ]

        return ribhandler.RibCollection(table, self)


def main(config_file_path):
    """本体."""
    config = Config(config_file_path)

    ribs = config.read_rib_specs()

    ribs.read_unique_airfoils(config.dat_directory)

    ribs.draw_each(config.save_directory)

    print('process successfully completed')


if __name__ == '__main__':
    main(CONFIG_DIRECTORY+'config.csv')

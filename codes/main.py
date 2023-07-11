# coding:utf-8

"""翼リブ図面自動描画プログラムの本体."""

import ribhandler
import os

DATA_DIRECTORY: str = os.path.dirname(__file__) + "/../data/"
AIRFOIL_DIRECTORY: str = DATA_DIRECTORY + "airfoils/"
SAVE_DIRECTORY: str = DATA_DIRECTORY + "figure/"
CONFIG_DIRECTORY: str = DATA_DIRECTORY + "config/"


def main(config_file_name):
    """本体."""
    # config = Config(config_file_path)

    # ribs = config.read_rib_specs()

    ribs = ribhandler.RibCollection()
    ribs.load_config(CONFIG_DIRECTORY, config_file_name)

    ribs.read_unique_airfoils(AIRFOIL_DIRECTORY)

    ribs.draw_each(SAVE_DIRECTORY)

    print("process successfully completed")


if __name__ == "__main__":
    main("config.csv")

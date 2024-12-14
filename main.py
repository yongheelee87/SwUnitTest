import yaml
from Lib.commons import SETTING_YAML
from Lib.generateTest import GenSWTest


if __name__ == "__main__":
    with open(SETTING_YAML, encoding='utf-8-sig', mode='r') as f:
        setting = yaml.load(f, Loader=yaml.SafeLoader)

    swTest = GenSWTest(gcc_option=setting["gcc_option"],
                       pjt=setting["project_path"],
                       compil_option=setting["compilation_option"],
                       source=setting["source_file"],
                       header=setting["header_file"])

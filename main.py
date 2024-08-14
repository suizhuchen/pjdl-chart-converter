# PJDLChartConverter
# Author:Suichen

import json
import math
import os
import random
import shutil
import string
import zipfile

# 一个意义不明的定义区域
chart_format_dict = {
    ".osz": '.osu',
    ".mcz": '.mc',
}


# 去除末尾的 .*
def remove_end_dot(string: str) -> str:
    # 将main_chart_file_name的.*后缀去除
    # 需考虑B.B.K.K.B.K.K.mcz的类似情况
    return string[:-len(string.split('.')[-1]) - 1]
    # 解释
    # # 找到 string 中最后一个. 的索引
    # last_dot_index = string.rfind('.')
    #
    # # 如果找不到.，则返回原字符串
    # if last_dot_index == -1:
    #     return string
    #
    # # 截取字符串，不包括最后一个.
    # return string[:last_dot_index]


# 获取末尾的.*
def get_end_dot(string: str) -> str:
    return string[-len(string.split('.')[-1]) - 1:]
    # # 截取字符串，不包括最后一个.
    # return string[last_dot_index:]


def gen_random_uid(length: int = 13) -> str:
    uid_random_str_list = list(string.ascii_lowercase) + list(string.digits)
    random_uid = ''
    for i in range(length):
        random_uid += uid_random_str_list[random.randint(0, len(uid_random_str_list) - 1)]
    return random_uid


def support_gbk(zip_file: zipfile.ZipFile):
    name_to_info = zip_file.NameToInfo
    # copy map first
    for name, info in name_to_info.copy().items():
        real_name = name.encode('cp437').decode('utf-8')
        if real_name != name:
            info.filename = real_name
            del name_to_info[name]
            name_to_info[real_name] = info
    return zip_file


def unzip_chinese(file_path: str, extract_path: str):
    with support_gbk(zipfile.ZipFile(file_path)) as supported_zfp:
        supported_zfp.extractall(extract_path)


class PJDLCConfig:
    def __init__(self, song_name, song_path, creator, info, bg, bpm, corrected, notes):
        self.song_name = song_name
        self.song_path = song_path
        self.creator = creator
        self.info = info
        self.bg = bg
        self.bpm = bpm
        self.corrected = corrected
        self.notes = notes

    def generate(self) -> dict:
        final_dict = dict()
        final_dict['author'] = self.creator
        final_dict['bpm'] = self.bpm
        final_dict['corrected'] = self.corrected
        final_dict['info'] = self.info
        final_dict['name'] = self.song_name
        final_dict['notes'] = self.notes
        final_dict['tags'] = []
        return final_dict

    def try_create_path(self) -> str:
        os.makedirs(f'export/{self.song_name}', exist_ok=True)
        # 建立文件夹成功或文件夹本身已存在，证明其合法
        # 合法后再次清空内容，防止离谱bug
        if not os.path.exists(f'export/{self.song_name}'):
            path_name = gen_random_uid()
        else:
            path_name = self.song_name
        if os.path.exists(f'export/{path_name}'):
            shutil.rmtree(f'export/{path_name}')
        if os.path.exists(f'export/{path_name}.pjdlc'):
            os.remove(f'export/{path_name}.pjdlc')
        os.makedirs(f'export/{path_name}')
        return f'export/{path_name}'


def osu_dict_process(osu_full: str) -> dict:
    with open(osu_full, 'r', encoding='UTF-8-sig') as f:
        osu_chart = f.read().split("\n")
    osu_chart_dict = dict()
    osu_temp_last_para = ''
    for i in osu_chart:
        # 新分节判定
        if i.startswith('[') and i.endswith(']'):
            osu_temp_last_para = i[1:-1]
        else:
            # 非空判断
            if i != "" and osu_temp_last_para != '':
                # 列表或键值对判断
                osu_temp_key_pair = i.split(': ')
                if len(osu_temp_key_pair) == 1:
                    # 列表
                    osu_temp_key_list = i.split(',')
                    osu_temp_combined_list = list()
                    for j in osu_temp_key_list:
                        osu_temp_combined_list.append(j)
                    if osu_chart_dict.get(osu_temp_last_para, None) is None:
                        osu_chart_dict[osu_temp_last_para] = list()
                    osu_chart_dict[osu_temp_last_para].append(osu_temp_combined_list)
                else:
                    if osu_chart_dict.get(osu_temp_last_para, None) is None:
                        osu_chart_dict[osu_temp_last_para] = dict()
                    osu_chart_dict[osu_temp_last_para][osu_temp_key_pair[0]] = osu_temp_key_pair[1]
    return osu_chart_dict


# 处理谱面信息
def process_chart_info(chart_type: str, chart_file_path: str, chart_file_name: str) -> 'PJDLCConfig':
    match chart_type:
        case '.osu':
            osu_chart_full = os.path.join(chart_file_path, chart_file_name)
            osu_chart_dict = osu_dict_process(osu_chart_full)
            # 谱面解析 Part 2
            # 提取必要信息
            # 因存储格式，导致数字以及其他类型数据均为文本
            if osu_chart_dict['General']['Mode'] != "3" and osu_chart_dict['Difficulty']['CircleSize'] != "4":
                raise Exception('非osu! mania 4k谱面')
            osu_song = osu_chart_dict['General']['AudioFilename']
            osu_song_name = osu_chart_dict['Metadata']['TitleUnicode']
            osu_creator = osu_chart_dict['Metadata']['Creator']
            osu_info = f'曲师：{osu_chart_dict['Metadata']['ArtistUnicode']}\n{osu_chart_dict['Metadata']['Version']}'
            osu_bg = ''
            for i in osu_chart_dict['Events']:
                if len(i) == 5 and i[0] == "0" and i[1] == "0":
                    osu_bg = i[2][1:-1]
                    break
            # 谱面解析 Part 3
            # 谱面主体解析
            osu_temp_beat_length = -1
            osu_temp_start_time = 0
            for i in osu_chart_dict['TimingPoints']:
                if i[6] == "1":
                    if osu_temp_beat_length != -1:
                        raise Exception("不支持变速谱")
                    osu_temp_beat_length = float(i[1])
                    osu_temp_start_time = int(i[0])
            osu_bpm = round(1 / osu_temp_beat_length * 1000 * 60, 3)
            # 20240809
            # 突然察觉到，不能以0 beat开头
            # 将corrected减去一拍长度
            osu_corrected = (osu_temp_start_time - osu_temp_beat_length) / 1000
            # 谱面解析 Part 3
            osu_notes = list()

            for i in osu_chart_dict['HitObjects']:
                osu_temp_note_key = math.floor(int(i[0]) * 4 / 512)
                osu_temp_note_time_start = int(i[2]) - osu_temp_start_time
                osu_temp_note_beat = osu_temp_note_time_start // osu_temp_beat_length + 1
                osu_temp_note_beat_i = round(
                    (osu_temp_note_time_start % osu_temp_beat_length) / osu_temp_beat_length * 48)
                if osu_temp_note_beat_i == 48:
                    osu_temp_note_beat += 1
                    osu_temp_note_beat_i = 0
                # 出现了令人难绷节拍偏移问题
                # 本来为了方便计算，将一拍时间简化为整数，可这会导致偏移，所以换回小数了
                osu_temp_note_beat = int(osu_temp_note_beat)
                if i[3] == "128":
                    # 长键
                    osu_temp_note_time_end = int(i[5].split(':')[0]) - osu_temp_start_time
                    osu_temp_note_drag = round(
                        (osu_temp_note_time_end - osu_temp_note_time_start) / osu_temp_beat_length * 48)
                    osu_notes.append([osu_temp_note_beat, osu_temp_note_beat_i, osu_temp_note_drag, osu_temp_note_key])

                else:
                    osu_notes.append([osu_temp_note_beat, osu_temp_note_beat_i, 0, osu_temp_note_key])
                # print(len(osu_notes) - 1, '：', osu_notes[len(osu_notes) - 1])
            return PJDLCConfig(osu_song_name, osu_song, osu_creator, osu_info, osu_bg, osu_bpm, osu_corrected,
                               osu_notes)

        case '.mc':
            malody_chart_full = os.path.join(chart_file_path, chart_file_name)
            with open(malody_chart_full, 'r', encoding='UTF-8') as f:
                malody_chart_dict = json.load(f)
            # 4k谱面检测
            if malody_chart_dict['meta']['mode_ext']['column'] != 4:
                raise Exception('非4k谱面，转换失败')
            # 非变速谱检测
            if len(malody_chart_dict['time']) != 1:
                raise Exception('谱面bpm非法（bpm信息错误/变速谱）')
            malody_song_name = malody_chart_dict['meta']['song']['title']
            malody_creator = malody_chart_dict['meta']['creator']
            malody_info = f'曲师：{malody_chart_dict['meta']['song']['artist']}\n{malody_chart_dict['meta']['version']}'
            malody_bg = malody_chart_dict['meta']['background']
            malody_bpm = malody_chart_dict['time'][0]['bpm']
            malody_notes = list()
            malody_corrected = float()
            malody_sound_path = ''
            # 主谱面提取
            # 20240810
            # 对于malody谱面，因为要提前offset，所以需要将beat提前
            # 询问处理力度
            print("\n对于malody谱面，需要将谱面偏移由负转正，因此需将谱面整体提前，对于提前的拍数，可以通过计算得来")
            print('对此，我们加入了处理力度的机制，其作用为将谱面偏移向正调整，同时将谱面向前调整的精度')
            print('比如力度为4，则会不停地以1/4拍为单位进行偏移与谱面的调整，直到偏移为正值')
            malody_temp_input = input("请输入处理力度（默认：4）：")
            if malody_temp_input == '':
                malody_offset_arg = 4
            else:
                malody_offset_arg = int(malody_temp_input)

            for malody_temp_note in malody_chart_dict['note']:
                malody_temp_note = dict(malody_temp_note)
                if malody_temp_note.get('column', -1) != -1:
                    # note种类判断
                    if malody_temp_note.get('endbeat', None) is not None:
                        # hold判定
                        malody_temp_beat_i = round(int(malody_temp_note['beat'][1]) * 48) / int(
                            malody_temp_note['beat'][2])
                        malody_temp_drag = (int(malody_temp_note['endbeat'][0]) - int(
                            malody_temp_note['beat'][0])) * 48 + (round(int(malody_temp_note['endbeat'][1]) * 48) / int(
                            malody_temp_note['endbeat'][2]) - malody_temp_beat_i)
                        if malody_temp_drag <= 0:
                            raise Exception(
                                f'程序失误了，将下面这段信息保存\n\n\n{malody_temp_note}|{malody_temp_beat_i}|{malody_temp_drag}')
                        single_note = [
                            malody_temp_note['beat'][0],
                            malody_temp_beat_i,
                            malody_temp_drag,
                            malody_temp_note['column']
                        ]
                    else:
                        malody_temp_beat_i = round(int(malody_temp_note['beat'][1]) * 48) / int(
                            malody_temp_note['beat'][2])
                        single_note = [
                            malody_temp_note['beat'][0],
                            malody_temp_beat_i,
                            0,
                            malody_temp_note['column']
                        ]
                    malody_notes.append(single_note)
                else:
                    malody_corrected = -int(malody_temp_note['offset'])
                    malody_sound_path = malody_temp_note['sound']

            # 20240809
            # 你说得对，但是谱面偏移不能为负
            # 浅浅的计算一下
            # 首先，bpm的数值应该如何转换为一拍的时间
            # bpm为拍数每分钟，那么一拍的时间为60000/bpm，单位为毫秒
            # 我们在谱面所有信息提取完毕了再进行处理
            malody_chart_bpm_time = 60000 / malody_bpm
            malody_temp_correct_time = 0
            if malody_corrected < 0:
                malody_temp_adding_offset = malody_chart_bpm_time * (1 / malody_offset_arg)
                while malody_corrected < 0:
                    malody_corrected += malody_temp_adding_offset
                    malody_corrected = round(malody_corrected, 3)  # 四舍五入
                    malody_temp_correct_time += 1
                # 现在延迟非零，将延迟单位由ms改为s
                malody_corrected /= 1000
                # 将谱面整体提前
                malody_temp_adding_offset = malody_temp_correct_time * (1 / malody_offset_arg) * 48
                for i in malody_notes:
                    i[1] -= malody_temp_adding_offset
                    while i[1] < 0:
                        i[1] += 48
                        i[0] -= 1
                    if i[0] < 0:
                        raise Exception('谱面错误，谱面整体提前{malody_temp_correct_time}拍，导致拍数为负')
            # 谱面解析 Part 3
            return PJDLCConfig(malody_song_name, malody_sound_path, malody_creator, malody_info, malody_bg,
                               malody_bpm, malody_corrected, malody_notes)
        case _:
            raise ValueError('1.谱面格式暂不支持 2.本报错位于处理谱面信息，前方检查未报错')


def chart_name_display(choose_chart_file_path: str, choose_chart_format: str) -> [str, str]:
    if chart_format not in chart_format_dict.values():
        raise ValueError('谱面格式错误')
    _chart_list = list()
    # 遍历当前py文件目录下除了py后缀的所有文件，排除文件夹:
    for root, dirs, files in os.walk(choose_chart_file_path):
        for _file in files:
            relative_path = os.path.relpath(os.path.join(root, _file), choose_chart_file_path)
            full_path = os.path.join(root, _file)
            if full_path.endswith(choose_chart_format):
                match choose_chart_format:
                    case '.osu':
                        osu_chart_dict = osu_dict_process(full_path)
                        _chart_list.append(relative_path)
                        print(f'{len(_chart_list) - 1}：{osu_chart_dict['Metadata']['Version']}')
                    case '.mc':
                        with open(full_path, 'r', encoding='UTF-8') as f:
                            malody_chart_dict = json.load(f)
                            _chart_list.append(relative_path)
                            print(f'{len(_chart_list) - 1}：{malody_chart_dict['meta']['version']}')
                    case _:
                        raise ValueError('1.谱面格式暂不支持 2.本报错位于处理谱面信息，前方检查未报错')
    chart_index = int(input('\n请输入欲转换谱面文件序号：'))
    if chart_index not in range(0, len(_chart_list)):
        raise ValueError('谱面文件序号错误')
    # 此处main_chart_file_name仅为文件名本身（比如123.mcz），path则不包含文件名，仅目录
    # 仅适配Windows平台，采取反斜杠进行目录分割（因为PJDL目前也只输出了Windows平台，需要改了再改罢（叹气
    return_chart_file_name = _chart_list[chart_index].split('\\')[-1]
    return_chart_file_path = os.path.join(zipped_chart_file_path, os.path.dirname(_chart_list[chart_index]))
    # 进入不同的谱面处理环节
    return return_chart_file_name, return_chart_file_path


if __name__ == '__main__':
    global zipped_chart_file_path, export_path
    print('欢迎使用PJDLC谱面文件转换工具')
    print('目前支持malody, osu! mania的4k谱面文件转换')
    print()
    print('请选择欲转换谱面文件\n')
    try:
        # 遍历当前py文件目录下除了py后缀的所有文件，排除文件夹
        file_list = list()
        for file in os.listdir(os.path.dirname(__file__)):
            if not file.endswith('.py') and not os.path.isdir(file):
                file_list.append(file)
                print(f'{len(file_list) - 1}：{file}')
        file_index = int(input('\n请输入欲转换谱面文件序号：'))
        if file_index not in range(0, len(file_list)):
            raise ValueError('谱面文件序号错误')
        zipped_chart_file_name = file_list[file_index]
        zipped_chart_file_path = remove_end_dot(zipped_chart_file_name)
        # 既然文件名是读取来的，证明其本身是合法的，因此无需校验
        # 清理临时目录
        if os.path.exists(zipped_chart_file_path):
            shutil.rmtree(zipped_chart_file_path)
        # 解压 适配UTF-8（适配中文）
        # shutil.unpack_archive(zipped_chart_file_name, zipped_chart_file_path, format='zip')
        unzip_chinese(zipped_chart_file_name, zipped_chart_file_path)
        # 根据谱面文件格式进行分别操作

        if chart_format_dict.get(get_end_dot(zipped_chart_file_name), None) is None:
            raise ValueError('谱面文件格式错误')
        chart_format = chart_format_dict[get_end_dot(zipped_chart_file_name)]
        chart_list = list()
        # 20240814
        # 优化了对谱面文件的判断
        # 不再显示文件名而是直接显示难度
        main_chart_file_name, main_chart_file_path = chart_name_display(zipped_chart_file_path, chart_format)
        config = process_chart_info(chart_format, main_chart_file_path, main_chart_file_name)

        export_path = config.try_create_path()
        shutil.copy(str(os.path.join(main_chart_file_path, config.song_path)), os.path.join(export_path, 'song.ogg'))
        shutil.copy(str(os.path.join(main_chart_file_path, config.bg)), os.path.join(export_path, 'cover.jpg'))
        with open(os.path.join(export_path, 'chart.json'), 'w', encoding='UTF-8') as f:
            json.dump(config.generate(), f, ensure_ascii=False, indent=None)
        # 将export_path里的3个文件压缩成zip
        shutil.make_archive(export_path, 'zip', export_path)
        # 将后缀从zip改为pjdlc
        os.rename(f'{export_path}.zip', f'{export_path}.pjdlc')
        print(f'\n转换成功，文件已导出至{export_path}.pjdlc')
    except Exception as e:
        print('\n[程序报错]')
        # 输出更多信息，比如文件名，报错行数
        print(f'错误信息：{e}')
        print(f'错误类型：{type(e)}')
        print(f'错误行数：{e.__traceback__.tb_lineno}')
        print(f'错误文件名：{e.__traceback__.tb_frame.f_code.co_filename}')
    finally:
        print('\n正在进行清理操作...')
        try:
            # 尝试清理，一般报错未定义，则代表那块目录肯定没有
            if os.path.exists(zipped_chart_file_path):
                shutil.rmtree(zipped_chart_file_path)
            if os.path.exists(export_path):
                shutil.rmtree(export_path)
        except:
            pass
        input('\n程序运行结束，按回车退出...')

# PJDL Chart Converter Remake
# Author: Suichen
import argparse
import math
import os
from sys import stderr, stdout
import json
from zipfile import ZipFile
import shutil
import subprocess
from PIL import Image

SUPPORTED_TYPES = ['malody', 'osu']
RUNNING_TYPES = ['difficulty', 'convert', 'unzip', 'pack', 'picture', 'music']

parser = None


def output_error(error_msg):
    stderr.write(json.dumps({'code': 1, 'error': error_msg}))


def output_info(message):
    stdout.write(json.dumps({'code': 0, 'result': message}))


class Chart:
    def __init__(self, song_name, song_path, creator, info, bg, bpm, corrected, notes):
        self.song_name = song_name
        self.song_path = song_path
        self.creator = creator
        self.info = info
        self.bg = bg
        self.bpm = bpm
        self.corrected = corrected
        self.notes = notes

    def write_to_file(self, output_file):
        with open(output_file, 'w', encoding='UTF-8') as f:
            json.dump({
                'name': self.song_name,
                'author': self.creator,
                'info': self.info,
                'bpm': self.bpm,
                'corrected': self.corrected,
                'notes': self.notes,

            }, f, indent=4, ensure_ascii=False)


def osu_chart_parser(chart_file):
    # osu谱面是否存在
    if not os.path.exists(chart_file):
        output_error(f'Chart file not found: {chart_file}\n')

    # 读取谱面文件
    with open(chart_file, 'r', encoding='UTF-8-sig') as f:
        osu_chart = f.read()

    # 解析谱面信息
    osu_chart_lines = osu_chart.split('\n')
    dict_chart = {}
    now_key = ''
    for line in osu_chart_lines:
        if line.startswith('['):
            now_key = line.strip('[]')
            continue
        key_value = line.strip().split(':')
        if len(key_value) == 2:
            if dict_chart.get(now_key, None) is None:
                dict_chart[now_key] = {}
            dict_chart[now_key][key_value[0].strip()] = key_value[1].strip()
        else:
            if now_key == '' or line.strip() == '' or line.strip().startswith('//'):
                continue
            append_list = []
            small_append_list = []
            list_value = line.strip().split(',')
            for value in list_value:
                split_value = value.strip().split(':')
                if len(split_value) == 1:
                    append_list.append(value.strip().strip('"'))
                else:
                    # 分割为一个list
                    for i in split_value:
                        # 去除空格和双引号
                        small_append_list.append(i.strip().strip('"'))
                    append_list.append(small_append_list)
                    small_append_list = []
            if dict_chart.get(now_key, None) is None:
                dict_chart[now_key] = []
            dict_chart[now_key].append(append_list)
    return dict_chart


def parse_args():
    global parser
    parser = argparse.ArgumentParser(description='PJDL Chart Converter Remake')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1.0')
    parser.add_argument('-t', '--type', dest='running_type',
                        help='Program running type. Possible values: "difficulty" for getting difficulty version of'
                             'charts, "convert" for converting charts. "unzip" for unzipping charts. "pack" for '
                             'packing charts. "picture" for converting picture of charts. "music" for converting '
                             'music of charts.',
                        required=True)
    parser.add_argument('-c', '--chart', dest='input_chart_type',
                        help=f'Chart type. Possible values: {", ".join(SUPPORTED_TYPES)}',
                        required=True)
    parser.add_argument('-i', '--input', dest='input_file', help='Input file path', required=True)
    parser.add_argument('-o', '--output', dest='output_file', help='Output file path', required=True)

    args = parser.parse_args()
    # 检测运行类型是否合法
    if args.running_type not in RUNNING_TYPES:
        output_error(f'Invalid running type: {args.running_type}. Possible values: {", ".join(RUNNING_TYPES)}')
    # 检测谱面类型是否合法
    if args.input_chart_type not in SUPPORTED_TYPES:
        output_error(f'Invalid chart type: {args.input_chart_type}. Possible values: {", ".join(SUPPORTED_TYPES)}')
    return args.running_type, args.input_chart_type, args.input_file, args.output_file


def parse_chart(chart_type, input_file):
    # 谱面文件是否存在
    if not os.path.exists(input_file):
        output_error(f'Chart file not found: {input_file}\n')
    match chart_type:
        case 'malody':
            malody_chart = json.load(open(input_file, 'r', encoding='utf-8'))
            # 4k谱面检测
            if malody_chart['meta']['mode_ext']['column'] != 4:
                output_error('非4k谱面，转换失败')
            # 非变速谱检测
            if len(malody_chart['time']) != 1:
                output_error('谱面bpm非法（bpm信息错误/变速谱）')
            malody_song_name = malody_chart['meta']['song']['title'].strip()
            malody_creator = malody_chart['meta']['creator'].strip()
            malody_info = f'曲师：{malody_chart['meta']['song']['artist']}\n{malody_chart['meta']['version']}'.strip()
            malody_bg = malody_chart['meta']['background'].strip()
            malody_bpm = malody_chart['time'][0]['bpm']
            malody_notes = list()
            malody_corrected = float()
            malody_sound_path = ''

            for malody_temp_note in malody_chart['note']:
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
                            output_error(
                                f'Malody hold note error: {malody_temp_note}|{malody_temp_beat_i}|{malody_temp_drag}')
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
                    malody_corrected = round(-(int(malody_temp_note['offset']) / 1000), 3)
                    malody_sound_path = malody_temp_note['sound']
            return Chart(malody_song_name, malody_sound_path, malody_creator, malody_info, malody_bg, malody_bpm,
                         malody_corrected, malody_notes)
        case 'osu':
            osu_chart = osu_chart_parser(input_file)
            # 谱面信息获取
            if osu_chart['General']['Mode'] != "3" and osu_chart['Difficulty']['CircleSize'] != "4":
                output_error('非osu! mania 4k谱面')
            osu_song = osu_chart['General']['AudioFilename'].strip()
            osu_song_name = osu_chart['Metadata']['TitleUnicode'].strip()
            osu_creator = osu_chart['Metadata']['Creator'].strip()
            osu_info = f'曲师：{osu_chart['Metadata']['ArtistUnicode']}\n{osu_chart['Metadata']['Version']}'.strip()
            osu_bg = ''
            for i in osu_chart['Events']:
                if len(i) == 5 and i[0] == "0" and i[1] == "0":
                    osu_bg = i[2].strip()
                    break
            # 谱面解析 Part 3
            # 谱面主体解析
            osu_temp_beat_length = -1
            osu_temp_start_time = 0
            for i in osu_chart['TimingPoints']:
                if i[6] == "1":
                    if osu_temp_beat_length != -1:
                        output_error("不支持变速谱")
                    osu_temp_beat_length = float(i[1])
                    osu_temp_start_time = int(i[0])
            osu_bpm = round(1 / osu_temp_beat_length * 1000 * 60, 3)
            osu_notes = list()
            # 计算最小整拍事件以提前
            osu_min_beat = osu_temp_start_time // osu_temp_beat_length
            osu_corrected = round((osu_temp_start_time - osu_min_beat * osu_temp_beat_length) / 1000, 3)
            for i in osu_chart['HitObjects']:
                osu_temp_note_key = math.floor(int(i[0]) * 4 / 512)
                osu_temp_note_time_start = int(i[2]) - osu_temp_start_time
                osu_temp_note_beat = osu_temp_note_time_start // osu_temp_beat_length + osu_min_beat
                osu_temp_note_beat_i = round(
                    (osu_temp_note_time_start % osu_temp_beat_length) / osu_temp_beat_length * 48)
                while osu_temp_note_beat_i >= 48:
                    osu_temp_note_beat += 1
                    osu_temp_note_beat_i -= 48
                # 出现了令人难绷节拍偏移问题
                # 本来为了方便计算，将一拍时间简化为整数，可这会导致偏移，所以换回小数了
                osu_temp_note_beat = int(osu_temp_note_beat)
                if i[3] == "128":
                    # 长键
                    osu_temp_note_time_end = int(i[5][0]) - osu_temp_start_time
                    osu_temp_note_drag = round(
                        (osu_temp_note_time_end - osu_temp_note_time_start) / osu_temp_beat_length * 48)
                    osu_notes.append([osu_temp_note_beat, osu_temp_note_beat_i, osu_temp_note_drag, osu_temp_note_key])

                else:
                    osu_notes.append([osu_temp_note_beat, osu_temp_note_beat_i, 0, osu_temp_note_key])
            return Chart(osu_song_name, osu_song, osu_creator, osu_info, osu_bg, osu_bpm, osu_corrected, osu_notes)


def basic_parse_info(chart_type, input_file):
    match chart_type:
        case 'malody':
            malody_chart = json.load(open(input_file, 'r', encoding='utf-8'))
            return malody_chart['meta']['version']
        case 'osu':
            osu_chart = osu_chart_parser(input_file)
            return osu_chart['Metadata']['Version']


def type_action(chart_type, input_file, output_file, running_type):
    match running_type:
        case 'difficulty':
            output_info(basic_parse_info(chart_type, input_file))
        case 'convert':
            chart = parse_chart(chart_type, input_file)
            chart.write_to_file(output_file)
            output_info({
                'song_path': chart.song_path,
                "cover_path": chart.bg,
                'chart_path': output_file,
            })
        case 'unzip':
            if os.path.exists(output_file):
                shutil.rmtree(output_file)
            os.makedirs(output_file)
            with ZipFile(input_file, 'r', metadata_encoding='utf-8') as zip_file:
                zip_file.extractall(os.path.dirname(output_file))
            output_info(f'Unzipped to {os.path.dirname(output_file)}')
        case 'pack':
            if not os.path.exists(input_file):
                output_error(f'Path not found: {input_file}\n')
            # 是否为目录
            if not os.path.isdir(input_file):
                output_error(f'Input file is not a directory: {input_file}\n')
            else:
                # 压缩文件
                shutil.make_archive(output_file, 'zip', input_file)
        case 'picture':
            if not os.path.exists(input_file):
                output_error(f'Path not found: {input_file}\n')
            try:
                img = Image.open(input_file)
                img.save(output_file)
                output_info(f'Picture convert success: {output_file}\n')
            except:
                output_error(f'Picture convert failed: {input_file}\n')
        case 'music':
            if not os.path.exists(input_file):
                output_error(f'Path not found: {input_file}\n')
            try:
                subprocess.run(['ffmpeg', '-i', input_file, '-acodec', 'libvorbis', output_file], check=True)
                output_info(f'Music convert success: {output_file}\n')
            except:
                output_error(f'Music convert failed: {input_file}\n')


if __name__ == '__main__':
    running_type, input_chart_type, input_file, output_file = parse_args()
    type_action(input_chart_type, input_file, output_file, running_type)

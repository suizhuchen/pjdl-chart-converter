# PJDL Chart Converter Remake
# Author: Suichen
import math
import time
from typing import Union
import json


class PJDLChart:
    def __init__(self, song_name: str, song_path: str, creator: str, author: str, version: str, info: str, bg: str,
                 bpm: float,
                 corrected: float,
                 notes: list):
        self.song_name = song_name
        self.song_path = song_path
        self.creator = creator
        self.author = author
        self.version = version
        self.bg = bg
        self.bpm = bpm
        self.corrected = corrected
        self.notes = notes
        self.info = info

    def __str__(self):
        return (
            f"Song Name: {self.song_name}\nSong Path: {self.song_path}\nCreator: {self.creator}\n"
            f"Author: {self.author}\n"
            f"Version: {self.version}\nInfo: {self.info}\n"
            f"Background: {self.bg}\nBPM: {self.bpm}\nCorrected: {self.corrected}\nNotes: {self.notes}")

    @staticmethod
    def generate_from_chart(chart_string: str, chart_type: str) -> Union['PJDLChart', str]:
        match chart_type:
            case 'pjdl':
                chart_dict = json.loads(chart_string)
                song_name = chart_dict['name']
                song_path = 'song.ogg'
                creator = chart_dict['author']
                info = chart_dict['info']
                author = 'Various Artists'
                version = 'Converted from PJDL'
                bg = 'cover.jpg'
                bpm = chart_dict['bpm']
                corrected = chart_dict['corrected']
                notes = chart_dict['notes']
                return PJDLChart(song_name, song_path, creator, author, version, info, bg, bpm, corrected, notes)
            case 'malody':
                chart_dict = json.loads(chart_string)
                # 存在slide或其他模式不存在column的情况，因此使用get赋予默认值
                if chart_dict.get('meta', -1).get('mode_ext', -1).get('column', -1) != 4:
                    return "不支持非4key谱面"
                if len(chart_dict['time']) != 1:
                    return '谱面bpm非法（bpm信息错误/变速谱）'
                song_name = chart_dict['meta']['song']['title'].strip()
                creator = chart_dict['meta']['creator'].strip()
                author = chart_dict['meta']['song']['artist'].strip()
                version = chart_dict['meta']['version'].strip()
                info = ''
                bg = chart_dict['meta']['background'].strip()
                bpm = chart_dict['time'][0]['bpm']
                notes = list()
                corrected = float()
                sound_path = ''
                for note in chart_dict['note']:
                    note = dict(note)
                    # 先判断此音符非描述偏移与音频名音符
                    if note.get('column', None) is not None:
                        beat, a, b = note['beat']
                        beat_i = round(a * 48 / b)
                        column = note['column']
                        # 再判断是否为长条
                        if note.get('endbeat', None) is not None:
                            # tap音符
                            end_beat, end_a, end_b = note['endbeat']
                            drag = (end_beat - beat) * 48 + round(end_a * 48 / end_b) - beat_i
                            drag = int(drag)
                            if drag < 0:
                                return f"音符长度非法，谱子本身有问题，报错note信息:{note}"
                        else:
                            drag = 0
                        notes.append([beat, beat_i, drag, column])
                    else:
                        corrected = round(-(int(note['offset']) / 1000), 3)
                        sound_path = note['sound'].strip()
                return PJDLChart(song_name, sound_path, creator, author, version, info, bg, bpm, corrected, notes)

            case 'osu':
                # 对于osu，我们需要先将osu格式转换为json，再进行分析
                origin_chart_lines = chart_string.split('\n')
                chart_dict = dict()
                current_key = ''
                for line in origin_chart_lines:
                    if line.startswith('['):
                        current_key = line.strip('[]')
                        continue
                    # 无效操作判断
                    if line.strip() == '' or line.strip().startswith('//'):
                        continue
                    # 思路如下：先尝试以冒号分割，len为2以上则可能为键值对，否则是逗号分割列表
                    # 而len为2以上的，则判断第一个元素内是否有逗号，有则是列表，否则为键值对
                    # 对于键值对，则将冒号分割结果第一个元素做key，后面元素拼接为value
                    # 对于列表，则重新将line以逗号分隔，再对每个元素，是否有冒号，有则再分割为list，否则直接append
                    # 最后将所有键值对和列表合并到chart_dict中

                    # 进行操作前，先确定已经存在current_key
                    if current_key == '':
                        continue

                    key_value = line.strip().split(':')
                    if len(key_value) > 1:
                        # 可能为键值对
                        key = key_value[0].strip()
                        if ',' not in key:
                            # 确认为键值对
                            value = ':'.join(key_value[1:]).strip()
                            if current_key not in chart_dict:
                                chart_dict[current_key] = dict()
                            chart_dict[current_key][key] = value
                            # 后续情况皆为list，因此直接continue
                            continue
                    # 列表
                    list_value = line.strip().split(',')
                    current_list = []

                    for item in list_value:
                        if ':' in item:
                            # 非文件名（引号包裹）
                            if item.startswith('"') and item.endswith('"'):
                                item = item[1:-1].strip()
                                current_list.append(item)
                            else:
                                # small_list也可能存在带冒号的文件名，但是那块我们不管，我们不需要那么多信息
                                # 所以直接append
                                small_list = item.strip().split(':')
                                current_list.append(small_list)
                        else:
                            current_list.append(item.strip())
                    if current_key not in chart_dict:
                        chart_dict[current_key] = []
                    chart_dict[current_key].append(current_list)

                # 分析chart_dict
                if chart_dict['General']['Mode'] != "3" and chart_dict['Difficulty']['CircleSize'] != "4":
                    return "不支持非4key谱面"
                song_path = chart_dict['General']['AudioFilename'].strip()
                song_name = chart_dict['Metadata']['TitleUnicode'].strip()
                creator = chart_dict['Metadata']['Creator'].strip()
                author = chart_dict['Metadata']['ArtistUnicode'].strip()
                version = chart_dict['Metadata']['Version'].strip()
                info = ''
                bg = ''
                for i in chart_dict['Events']:
                    if len(i) == 5 and i[0] == "0" and i[1] == "0":
                        bg = i[2].strip()
                        break
                beat_length = -1
                # 此start time代表第一个TimingPoint的时间，note time start 代表当前note的开始时间
                start_time = 0
                for i in chart_dict['TimingPoints']:
                    if i[6] == "1":
                        # 如果已经存在beat_length，说明已经有了bpm信息，代表变速谱，不支持
                        if beat_length != -1:
                            return "谱面bpm非法（bpm信息错误/变速谱）"
                        beat_length = float(i[1])
                        start_time = int(i[0])
                if beat_length == -1:
                    return "谱面bpm非法（bpm信息错误/缺少bpm信息）"
                bpm = round(1 / beat_length * 1000 * 60, 3)
                notes = list()
                min_offset_beat = start_time // beat_length
                corrected = round((start_time - min_offset_beat * beat_length) / 1000, 3)
                for i in chart_dict['HitObjects']:
                    x, y, time, note_type, hitsound, extra = i
                    # 这里基本上没变，仅将数组切片改成了对应变量
                    key = math.floor(int(x) * 4 / 512)
                    note_time_start = int(time) - start_time
                    beat = int(note_time_start // beat_length + min_offset_beat)
                    beat_i = round((note_time_start % beat_length) / beat_length * 48)
                    while beat_i >= 48:
                        beat += 1
                        beat_i -= 48

                    if note_type == '128':
                        # 长条
                        note_end_time = int(extra[0]) - start_time
                        drag = round((note_end_time - note_time_start) / beat_length * 48)
                    else:
                        drag = 0
                    notes.append([beat, beat_i, drag, key])
                return PJDLChart(song_name, song_path, creator, author, version, info, bg, bpm, corrected, notes)

            case _:
                return "非法的谱面类型"

    def generate_to_chart(self, chart_type: str) -> str:
        match chart_type:
            case 'pjdl':
                info = f'曲师:{self.author}\n难度:{self.version}' if self.info == '' else self.info
                chart_dict = {
                    'author': self.creator,
                    'bpm': self.bpm,
                    'corrected': self.corrected,
                    'info': info,
                    'name': self.song_name,
                    'notes': self.notes
                }
                return json.dumps(chart_dict, ensure_ascii=False)
            case 'malody':
                chart_dict = {
                    'meta': {
                        "$ver": 0,
                        'creator': self.creator,
                        'background': self.bg,
                        'version': 'PJDL Chart Convert' if self.version == '' else self.version,
                        'id': 0,
                        'time': int(time.time()),
                        'song': {
                            'title': self.song_name,
                            'artist': 'Various Artists' if self.author == '' else self.author,
                            'id': 0
                        },
                        "mode_ext": {
                            "column": 4,
                            "bar_begin": 0
                        }
                    },
                    'time': [{
                        'beat': [0, 0, 1],
                        'bpm': self.bpm
                    }],
                    'effect': [],
                    'note': [],
                    'extra': {
                        'test': {
                            'divide': 4,
                            'speed': 100,
                            'save': 0,
                            'lock': 0,
                            'edit_mode': 0
                        }
                    }
                }
                for note in self.notes:
                    malody_note = {}
                    beat, beat_i, drag, column = note
                    beat = beat + beat_i // 48
                    a = beat_i % 48
                    malody_note['beat'] = [beat, a, 48]
                    # 进行慵懒地处理, 分子就是beat_i，分母就是48
                    if drag != 0:
                        end_beat = beat + (a + drag) // 48
                        end_a = (a + drag) % 48
                        malody_note['endbeat'] = [end_beat, end_a, 48]
                    malody_note['column'] = column
                    chart_dict['note'].append(malody_note)
                chart_dict['note'].append({
                    'beat': [0, 0, 1],
                    'sound': self.song_path,
                    'vol': 100,
                    'offset': int(-self.corrected * 1000),
                    'type': 1
                })
                return json.dumps(chart_dict, ensure_ascii=False)
            case 'osu':
                # 这里其实无非就是转换为osu的格式，依然是文本的拼接
                # 先计算一些东西
                offset = self.corrected * 1000
                single_beat_ms = 1 / (self.bpm / 60000)

                note_text = ''
                for note in self.notes:
                    beat, beat_i, drag, key = note
                    beat_ms = round(offset + single_beat_ms * beat + beat_i / 48 * single_beat_ms)
                    y = 192
                    x_dict = {
                        0: 0,
                        1: 128,
                        2: 256,
                        3: 384
                    }
                    x = x_dict[key]
                    if drag != 0:
                        end_time = beat_ms + round(drag / 48 * single_beat_ms)
                        this_note_text = f'{x},{y},{beat_ms},128,0,{end_time}:0:0:0:0:'
                    else:
                        this_note_text = f'{x},{y},{beat_ms},1,0,0:0:0:0:'
                    note_text += this_note_text + '\n'

                osu_string = \
                    f'''
osu file format v128

[General]
AudioFilename: {self.song_path}
Countdown: 0
Mode: 3

[Metadata]
Title: {self.song_name}
TitleUnicode: {self.song_name}
Artist: {self.author}
ArtistUnicode: {self.author}
Creator: {self.creator}
Version: {self.version}
Source: PJDLChartConverter
Tags: PJDL
BeatmapID: 0
BeatmapSbpetID: 0

[Difficulty]
HPDrainRate: 7.5
CircleSize: 4
OverallDifficulty: 7.5
ApproachRate: 5
SliderMultiplier: 1.4
SliderTickRate: 1

[Events]
0,0,"{self.bg}",0,0

[TimingPoints]
{offset},{single_beat_ms},4,0,0,100,1,1

[HitObjects]
{note_text}
'''
                # 部分注释
                # 不知道General的AudioFilename是否支持ogg，先支持再说
                # 大部分内容直接采取默认值
                # 跳过Editor部分，因为我不知道怎么写
                # 罗马音，我懒得转了

                return osu_string[1:-1]
            case _:
                return "非法的谱面类型"


if __name__ == '__main__':
    with open('chart.json', 'r', encoding='utf-8') as f:
        chart_string = f.read()
    chart = PJDLChart.generate_from_chart(chart_string, 'pjdl')
    print(chart)
    chart_string = chart.generate_to_chart('osu')
    with open('chart.osu', 'w', encoding='utf-8') as f:
        f.write(chart_string)

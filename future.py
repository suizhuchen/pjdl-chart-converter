# PJDLChartConverter
# Author:Suichen

# A class based converter, developing
# Hard to finish...

import shutil
import os
import typing


class RhythmGameChartTranslator:
    zipped_file_format = '.zip'

    def __init__(self, chart_file_name, chart_file_path):
        self.chart_file_name = chart_file_name
        self.chart_file_path = chart_file_path

    @staticmethod
    def gen(chart_file_name, chart_file_path):
        return RhythmGameChartTranslator(chart_file_name, chart_file_path)

    @staticmethod
    def get_format(return_type: int):
        match return_type:
            case 1:
                return RhythmGameChartTranslator.zipped_file_format
            case 2:
                return RhythmGameChartTranslator.gen


class OSU(RhythmGameChartTranslator):
    zipped_file_format = '.osz'

    def __init__(self, chart_file_name, chart_file_path):
        super().__init__(chart_file_name, chart_file_path)

    @classmethod
    def get_format(cls, return_type):
        match return_type:
            case 1:
                return cls.zipped_file_format
            case 2:
                return cls.gen

    @staticmethod
    def gen(chart_file_name, chart_file_path):
        return OSU(chart_file_name, chart_file_path)


class RhythmGameChartFormatClassifier:
    # 此处添加解析器
    format_list = list()
    format_list.append(OSU.get_format)

    @staticmethod
    def get_classification_type(zipped_file_name: str) -> int:
        for i in range(len(RhythmGameChartFormatClassifier.format_list)):
            if zipped_file_name.endswith(RhythmGameChartFormatClassifier.format_list[i](1)):
                return i

    @staticmethod
    def gen(type: int) -> typing.Callable:
        return RhythmGameChartFormatClassifier.format_list[type](2)


print(RhythmGameChartFormatClassifier.gen(RhythmGameChartFormatClassifier.get_classification_type('test.osz'))('test1',
                                                                                                               'test2').chart_file_name)

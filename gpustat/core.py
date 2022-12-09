#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import locale
import os.path
import platform
import sys
from datetime import datetime

from six.moves import cStringIO as StringIO

import psutil
import pynvml as N
from blessings import Terminal

NOT_SUPPORTED = 'Not Supported'
MB = 1024 * 1024
GB = 1024 * 1024*1024


class GPUStat(object):

    def __init__(self, entry):
        if not isinstance(entry, dict):
            raise TypeError(
                'entry should be a dict, {} given'.format(type(entry))
            )
        self.entry = entry

    def __repr__(self):
        return self.print_to(StringIO()).getvalue()

    def keys(self):
        return self.entry.keys()

    def __getitem__(self, key):
        return self.entry[key]

    # Python内置的@property装饰器就是负责把一个方法变成属性调用的：
    @property
    def index(self):
        """  Returns the index of GPU (as in nvidia-smi).  """
        return self.entry['index']

    @property
    def uuid(self):
        """  Returns the uuid returned by nvidia-smi,
        e.g. GPU-12345678-abcd-abcd-uuid-123456abcdef
        """
        return self.entry['uuid']

    @property
    def name(self):
        """  Returns the name of GPU card (e.g. Geforce Titan X)  """
        return self.entry['name']

    @property
    def memory_total(self):
        """  Returns the total memory (in GB) as an integer.  """
        return int(self.entry['memory.total'])

    @property
    def memory_used(self):
        return int(self.entry['memory.used'])

    @property
    def memory_free(self):
        v = self.memory_total - self.memory_used
        return max(v, 0)

    @property
    def temperature(self):
        """
        Returns the temperature (in celcius) of GPU as an integer,
        or None if the information is not available.
        """
        v = self.entry['temperature.gpu']
        return int(v) if v is not None else None

    @property
    def fan_speed(self):
        """
        Returns the fan speed percentage (0-100) of maximum intended speed
        as an integer, or None if the information is not available.
        """
        v = self.entry['fan.speed']
        return int(v) if v is not None else None

    @property
    def utilization(self):
        """
        Returns the GPU utilization (in percentile),
        or None if the information is not available.
        """
        v = self.entry['utilization.gpu']
        return int(v) if v is not None else None

    @property
    def power_used(self):
        """
        Returns the GPU power usage in Watts,
        or None if the information is not available.
        """
        v = self.entry['power.draw']
        return int(v) if v is not None else None

    @property
    def power_limit(self):
        v = self.entry['enforced.power.limit']
        return int(v) if v is not None else None

    @property
    def processes(self):
        """  Get the list of running processes on the GPU.  """
        return self.entry['processes']

    def print_to(self,
                 fp                          ,  # "fp" stands for "file pointer" and it was a pointer to a FILE structure in C
                 with_colors    = True       ,  # deprecated arg
                 show_cmd       = False      ,
                 show_user      = False      ,
                 your_name      = ''         ,
                 show_pid       = False      ,
                 show_power     = None       ,
                 show_fan_speed = None       ,
                 gpuName_width  = 16         ,
                 term           = Terminal() ,
                 no_gdm         = False      ,
                ):
        # color settings
        colors = {}

        def _conditional(cond_fn, true_value, false_value,
                         error_value=term.bold_black):
            try:
                return cond_fn() and true_value or false_value
            except Exception:
                return error_value

        colors['color_normal'] = term.normal
        colors['color_hi'] = term.cyan


        colors['FSpeed'] = _conditional(  lambda: self.fan_speed < 30,
                                        term.cyan,
                                        term.bold_cyan,
                                       )

        colors['color_MemU'] = term.bold_yellow
        colors['color_MemT'] = term.yellow
        colors['color_MemP'] = term.yellow
        colors['color_User'] = term.bold_black   # gray
        colors['color_Util'] = _conditional(lambda: self.utilization < 30,
                                       term.green, term.bold_green)
        colors['color_PowU'] = _conditional(
            lambda: float(self.power_used) / self.power_limit < 0.4,
            term.magenta, term.bold_magenta
        )
        colors['color_PowL'] = term.magenta

        if not with_colors:
            for k in list(colors.keys()):
                colors[k] = ''

        def _repr(v, none_value='??'):
            return none_value if v is None else v

        # ---build one-line display information---

        reps = "%(color_hi)s[{entry[index]}]%(color_normal)s"
        # 下面有:  reps = (reps) % colors
          #         # reps里有%(color_XXX)%s, 给colors插槽
        #         # 改成f-string反而不好

            # 暂时不需要:
            # we want power usage  optional,
                # but if deserves,
                # being grouped with  temperature and utilization

            #  reps = "%(color_hi)s[{entry[index]}]%(color_normal)s " \
            #      "%(color_hi)s{entry[name]:{gpuName_width}}%(color_normal)s |" \
            #      "%(color_hi)s{entry[temperature.gpu]:>3}'C%(color_normal)s, "


        if show_fan_speed:
            reps += "%(FSpeed)s{entry[fan.speed]:>3} %%%(color_normal)s, "

        #  reps += "%(color_Util)s{entry[utilization.gpu]:>3} %%%(color_normal)s"

        if show_power:
            reps += ",  %(color_PowU)s{entry[power.draw]:>3}%(color_normal)s "
            if show_power is True or 'limit' in show_power:
                reps += "/ %(color_PowL)s{entry[enforced.power.limit]:>3}%(color_normal)s "
                reps += "%(color_PowL)sW%(color_normal)s"
            else:
                reps += "%(color_PowU)sW%(color_normal)s"

        reps += "%(color_hi)s%(color_MemU)s{entry[memory.free]:>5}%(color_normal)s G"
            # 不行::
                # reps += f"{color_hi}{color_MemU}{entry[memory.free]:>5}{color_normal} G"
            # 啰嗦:
                #reps += " | %(color_hi)s%(color_MemU)s{entry[memory.used]:>5}%(color_normal)s " \
                    #  "/ %(color_MemT)s{entry[memory.total]:>5}%(color_normal)s "
        reps = (reps) % colors
                # reps里有%(color_XXX)%s, 给colors插槽
                # 改成f-string反而不好
        # print(f'{colors= }')  # 丑八怪的ANSI escape colors (是这么叫?)
        # print(f'{reps= }')

        reps = reps.format(entry = {k: _repr(v) for k, v in self.entry.items()},
                           gpuName_width = gpuName_width,
                          )
        reps += " | "
        def process_repr(p):  #  这是个递归函数
            r = ''

            if not show_cmd or show_user:
                r += "{color_User}{:8s}:{color_normal}".format( _repr(p['username'], '--'), **colors )
                              #  s前的数字: 字符串长度, 小于这个数就补空格
                              #  太小的话, 行与行之间容易对不齐
                              #  有的用户名:xxx2019,  7位
                              #  todo: 让这个数字 取出现的用户名的最大长度
            if show_cmd:
                if r:
                    r += ':'
                r += "{color_hi}{}{color_normal}".format( _repr(p.get('command', p['pid']), '--'), **colors)

            if show_pid:
                r += ("[%s]" % _repr(p['pid'], '--'))

            r += '{color_MemP}{:5.1f}G{color_normal}'.format( _repr(p['gpu_memory_usage'], '?'), **colors)
            return r

        processes = self.entry['processes']
        if processes is None:
            # None (not available)
            reps += ' ({})'.format(NOT_SUPPORTED)
        else:
            if your_name == '':
                for p in processes:
                    # reps +=  process_repr(p) + ' | '
                    if no_gdm :
                        if  _repr(p['username'], '--') != "gdm":
                            reps +=  process_repr(p) + ' | '
                    else:
                        reps +=  process_repr(p) + ' | '

            if your_name != '':
                for p in processes:
                    #only show process of user 'YOUR_NAME'
                    if _repr(p['username'], '--') == your_name:
                        reps += ' , ' + process_repr(p)

        fp.write(reps)
        return fp

    def jsonify(self):
        o = dict(self.entry)
        if self.entry['processes'] is not None:
            o['processes'] = [{k: v for (k, v) in p.items() if k != 'gpu_uuid'}
                              for p in self.entry['processes']]
        else:
            o['processes'] = '({})'.format(NOT_SUPPORTED)
        return o


class GPUStatCollection(object):

    def __init__(self, gpu_list, driver_version=None):
        self.gpus = gpu_list

        # attach additional system information
        self.hostname = platform.node()
        self.query_time = datetime.now()
        self.driver_version = driver_version

    @staticmethod
    def new_query():
        """Query the information of all the GPUs on local machine"""

        N.nvmlInit()

        def _decode(b):
            if isinstance(b, bytes):
                return b.decode()    # for python3, to unicode
            return b

        def get_gpu_info(handle):
            """Get one GPU information specified by nvml handle"""

            def get_process_info(nv_process):
                """Get the process information of specific pid"""
                process = {}
                ps_process = psutil.Process(pid=nv_process.pid)
                process['username'] = ps_process.username()
                # cmdline returns full path;
                # as in `ps -o comm`, get short cmdnames.
                _cmdline = ps_process.cmdline()
                if not _cmdline:
                    # sometimes, zombie or unknown (e.g. [kworker/8:2H])
                    process['command'] = 'leo_you_found_a_zombie'
                else:
                    process['command'] = os.path.basename(_cmdline[0])
                # Bytes to MBytes
                process['gpu_memory_usage'] = round(nv_process.usedGpuMemory/GB, 2)
                process['pid'] = nv_process.pid
                return process

            name = _decode(N.nvmlDeviceGetName(handle))
            uuid = _decode(N.nvmlDeviceGetUUID(handle))

            try:
                temperature = N.nvmlDeviceGetTemperature(
                    handle, N.NVML_TEMPERATURE_GPU
                )
            except N.NVMLError:
                temperature = None  # Not supported

            try:
                fan_speed = N.nvmlDeviceGetFanSpeed(handle)
            except N.NVMLError:
                fan_speed = None  # Not supported

            try:
                memory = N.nvmlDeviceGetMemoryInfo(handle)  # in Bytes
            except N.NVMLError:
                memory = None  # Not supported

            try:
                utilization = N.nvmlDeviceGetUtilizationRates(handle)
            except N.NVMLError:
                utilization = None  # Not supported

            try:
                power = N.nvmlDeviceGetPowerUsage(handle)
            except N.NVMLError:
                power = None

            try:
                power_limit = N.nvmlDeviceGetEnforcedPowerLimit(handle)
            except N.NVMLError:
                power_limit = None

            try:
                nv_comp_processes = \
                    N.nvmlDeviceGetComputeRunningProcesses(handle)
            except N.NVMLError:
                nv_comp_processes = None  # Not supported
            try:
                nv_graphics_processes = \
                    N.nvmlDeviceGetGraphicsRunningProcesses(handle)
            except N.NVMLError:
                nv_graphics_processes = None  # Not supported

            if nv_comp_processes is None and nv_graphics_processes is None:
                processes = None
            else:
                processes = []
                nv_comp_processes = nv_comp_processes or []
                nv_graphics_processes = nv_graphics_processes or []
                for nv_process in nv_comp_processes + nv_graphics_processes:
                    # TODO: could be more information such as system memory
                    # usage, CPU percentage, create time etc.
                    try:
                        process = get_process_info(nv_process)
                        processes.append(process)
                    except psutil.NoSuchProcess:
                        # TODO: add some reminder for NVML broken context
                        # e.g. nvidia-smi reset  or  reboot the system
                        pass

            index = N.nvmlDeviceGetIndex(handle)
            gpu_info = {
                'index'                : index       ,
                'uuid'                 : uuid        ,
                'name'                 : name        ,
                'temperature.gpu'      : temperature ,
                'fan.speed'            : fan_speed   ,
                'utilization.gpu'      : utilization.gpu \
                                            if utilization \
                                            else  \
                                       None,

                'power.draw'           : power // 1000 if power is not None else None,

                'enforced.power.limit' : power_limit // 1000 if power_limit is not None else None,
                # Convert bytes into MBytes
                'memory.used'          : memory.used / GB \
                                            if memory \
                                            else  \
                                        None,

                'memory.total'         : memory.total / GB if memory else None,

                'memory.free'          : round(max(0,(memory.total - memory.used)) / GB, 1) if memory else None,

                'processes'            : processes,
            }

            return gpu_info

        # 1. get the list of gpu and status
        gpu_list = []
        device_count = N.nvmlDeviceGetCount()

        for index in range(device_count):
            handle = N.nvmlDeviceGetHandleByIndex(index)
            gpu_info = get_gpu_info(handle)
            gpu_stat = GPUStat(gpu_info)
            gpu_list.append(gpu_stat)

        # 2. additional info (driver version, etc).
        try:
            driver_version = _decode(N.nvmlSystemGetDriverVersion())
        except N.NVMLError:
            driver_version = None    # N/A

        N.nvmlShutdown()
        return GPUStatCollection(gpu_list, driver_version=driver_version)

    def __len__(self):
        return len(self.gpus)

    def __iter__(self):
        return iter(self.gpus)

    def __getitem__(self, index):
        return self.gpus[index]

    def __repr__(self):
        s = 'GPUStatCollection(host=%s, [\n' % self.hostname
        s += '\n'.join('  ' + str(g) for g in self.gpus)
        s += '\n])'
        return s

    def print_formatted(self,
                        fp             = sys.stdout ,
                        force_color      = False      ,
                        no_color       = False      ,
                        show_cmd       = False      ,
                        show_user      = False      ,
                        your_name      = ''         ,
                        show_pid       = False      ,
                        show_power     = None       ,
                        show_fan_speed = None       ,
                        gpuName_width  = 16         ,
                        show_header    = True       ,
                        eol_char       = os.linesep ,
                        no_gdm         = False      ,
                       ):
        if 'ANSI color configuration' :
            if force_color and no_color:
                raise ValueError("--color(--force-color) and --no_color can't be used at the same time" )

            if force_color:
                t_color = Terminal(kind='linux', force_styling=True)

                # workaround of issue #32 (watch doesn't recognize sgr0 characters)
                t_color.normal = u'\x1b[0;10m'

            elif no_color:
                t_color = Terminal(force_styling=None)

            else:
                t_color = Terminal()   # auto, depending on isatty

        # appearance settings
        entry_name_width = [ len(gpu.entry['name']) for gpu in self ]
        gpuName_width    = max( entry_name_width + [ gpuName_width or 0 ]  )
                                                   # [ False or 666 ] 为 666
                                                   # [ True or 666 ] 为 [ True ]

        if show_header:
            time_format = locale.nl_langinfo(locale.D_T_FMT)

            header_template = '{t.bold_white}{hostname:{width}}{t.normal}  '
            header_template += '{timeStr}  '
            header_template += '{t.bold_black}{driver_version}{t.normal}'

            header_msg = header_template.format(hostname       = self.hostname                         ,
                                                width          = gpuName_width + 3                     ,
                                                timeStr        = self.query_time.strftime(time_format) ,
                                                driver_version = self.driver_version                   ,
                                                t              = t_color                               ,
                                               )

            fp.write(header_msg.strip())
            fp.write(eol_char)

        for gpu in self:
            gpu.print_to(fp,
                         show_cmd       = show_cmd       ,
                         show_user      = show_user      ,
                         your_name      = your_name      ,
                         show_pid       = show_pid       ,
                         show_power     = show_power     ,
                         show_fan_speed = show_fan_speed ,
                         gpuName_width  = gpuName_width  ,
                         term           = t_color        ,
                         no_gdm         = no_gdm         ,
                        )
            fp.write(eol_char)

        fp.flush()

    def jsonify(self):
        return {
            'hostname': self.hostname,
            'query_time': self.query_time,
            "gpus": [gpu.jsonify() for gpu in self]
        }

    def print_json(self, fp=sys.stdout):
        def date_handler(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            else:
                raise TypeError(type(obj))

        o = self.jsonify()
        json.dump( o, fp, indent=4, separators=(',', ': '), default=date_handler )
        fp.write('\n')
        fp.flush()


def new_query():
    '''
    Obtain a new GPUStatCollection instance by querying nvidia-smi
    to get the list of GPUs and running process information.
    '''
    return GPUStatCollection.new_query()

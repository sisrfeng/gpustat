gp () {
    echo '左侧是free Mem'
    gpustat --show-user --no-header $* | bat --language=go
    # using `go` is just for the beautiful color
}


ls_after_cd() {
    print ""
    # 放着, 方便搜索: auto_list_file_after_cd
    emulate -L zsh  # add this to  the body of your script or function
        # emulate: 模拟 csh ksh sh 或者 （没加配置的）zsh
                        # 这样可以 use zsh's `built-in features`,  避免setopt等搞乱默认配置
                        # to get round problems with options being changed in /etc/zshenv:
                            # put `emulate zsh' at the top of the script.
            # -L  | set local_options(activates LOCAL_OPTIONS) and local_traps as well
                        #                         trap命令:   trap 'echo "hi"' SIGINT
            # -R  | reset all options
            #        instead of only those needed for script portability
            #  另外 (unless  KSH_OPTION_PRINT  is  set),  `setopt' shows all options whose settings are changed from the default.

    # print "     ---${fg[cyan]}`pwd`${reset_color}----"  # 没必要了, 和新的ps1空了一行  (又过度用力 重复解决小问题了)

    # you need `brew install exa` to use this
    exa                           \
        -1                        \
        -F                        \
        --classify                \
        --colour=always           \
        --group-directories-first \
        --sort=time                 |
        tail -4                     |
        sed 's/^/    /'


    tmp=$((  `\ls -l | wc -l` - 1 - 4   ))
    #文件总数: `\ls -l | wc -l`-1

    if [ $tmp -lt 0 ]; then
        # echo "      ------没有其他文件了--------"
    else
        echo "          ----剩：$tmp----    "
    fi
}
alias nn='alias'  # nn: new name.  similar to `nnoremap` in vim
nn Date='date  +"%d日%H:%M:%S"'
nn Dating='print "  ---  `date  +"%d日%H:%M:%S"`   ---    \n"'


# python
    p(){
        if grep -q WSL2 /proc/version ; then
                \python3 -W ignore $*
        else
            # 不行:
                # functions_tmp=${chpwd_functions[@]} )
                # chpwd_functions=()
                # \python3 -W ignore $*
                # chpwd_functions=( ${functions_tmp[@]} )
                    # 执行这个函数导致 自动ls废了, chpwd_functions不能这么利用中间变量恢复?

            chpwd_functions=()
                local gpus=$( python3 find_gpus.py 4 )
                CUDA_VISIBLE_DEVICES=${gpus} python -W ignore -c 'import torch; print("gpu数量:", torch.cuda.device_count())'
                echo '使用gpu: '  ${gpus}
                CUDA_VISIBLE_DEVICES=${gpus} python -W ignore $*

            chpwd_functions=("chpwd_recent_dirs" "ls_after_cd" "Dating")
        fi
    }



    # nn b='pudb3'
    b(){
        if grep -q WSL2 /proc/version ; then
                pudb3 $*
        else
            chpwd_functions=()

                local gpus=$( python3 find_gpus.py 4 )
                CUDA_VISIBLE_DEVICES=${gpus} python -W ignore -c 'import torch; print("gpu数量:", torch.cuda.device_count())'
                echo '使用gpu: '  ${gpus}
                CUDA_VISIBLE_DEVICES=${gpus} \
                pudb3 $*

            chpwd_functions=("chpwd_recent_dirs" "ls_after_cd" "Dating")
        fi
    }


    nn pt='ptpython --vi'
    nn pti='ptipython --vi'


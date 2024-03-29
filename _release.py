import os
import re
import time
import webbrowser
from datetime import datetime

from _build import build
from _clear_github_artifact import clear_github_artifact
from _commit_new_version import commit_new_version
from _package import package
from _push_github import push_github
from alist import upload
from log import color, logger
from util import (
    change_console_window_mode_async,
    count_down,
    make_sure_dir_exists,
    pause_and_exit,
    range_from_one,
    show_head_line,
)
from version import now_version


def release():
    # ---------------准备工作
    prompt = f"如需直接使用默认版本号：{now_version} 请直接按回车\n或手动输入版本号后按回车："
    version = input(prompt) or now_version

    version_reg = r"\d+\.\d+\.\d+"

    if re.match(version_reg, version) is None:
        logger.info(f"版本号格式有误，正确的格式类似：1.0.0 ，而不是 {version}")
        pause_and_exit(-1)

    # 最大化窗口
    change_console_window_mode_async(disable_min_console=True)

    version = "v" + version

    run_start_time = datetime.now()
    show_head_line(f"开始发布版本 {version}", color("bold_yellow"))

    set_title_cmd = f"title 发布 {version}"
    os.system(set_title_cmd)

    # 先声明一些需要用到的目录的地址
    dir_src = os.path.realpath(".")
    dir_all_release = os.path.realpath(os.path.join("releases"))
    release_dir_name = f"DNF蚊子腿小助手_{version}_by风之凌殇"
    release_7z_name = f"{release_dir_name}.7z"
    dir_github_action_artifact = "_github_action_artifact"

    # ---------------构建
    # 调用构建脚本
    os.chdir(dir_src)
    build()

    # ---------------清除一些历史数据
    make_sure_dir_exists(dir_all_release)
    os.chdir(dir_all_release)
    clear_github_artifact(dir_all_release, dir_github_action_artifact)

    # ---------------打包
    os.chdir(dir_src)
    package(dir_src, dir_all_release, release_dir_name, release_7z_name, dir_github_action_artifact)

    # ---------------标记新版本
    show_head_line("提交版本和版本变更说明，并同步到docs目录，用于生成github pages", color("bold_yellow"))
    os.chdir(dir_src)
    commit_new_version()

    # ---------------上传到网盘
    show_head_line("开始上传到alist", color("bold_yellow"))
    os.chdir(dir_all_release)

    def path_in_src(filepath_relative_to_src: str) -> str:
        return os.path.realpath(os.path.join(dir_src, filepath_relative_to_src))

    realpath = os.path.realpath

    upload_list = [
        (realpath(release_7z_name), "DNF蚊子腿小助手_v"),
        (path_in_src("utils/auto_updater.exe"), ""),
        (path_in_src("使用教程/使用文档.docx"), ""),
        (path_in_src("使用教程/视频教程.txt"), ""),
        (path_in_src("付费指引/付费指引.docx"), ""),
    ]

    logger.info(color("bold_green") + "具体上传列表如下：")
    for local_filepath, _history_file_prefix in upload_list:
        logger.info(f"\t\t{local_filepath}")

    for local_filepath, history_file_prefix in reversed(upload_list):
        # 逆序遍历，确保同一个网盘目录中，列在前面的最后才上传，从而在网盘显示时显示在最前方
        total_try_count = 1
        for try_index in range_from_one(total_try_count):
            try:
                upload(local_filepath, old_version_name_prefix=history_file_prefix)
            except Exception:
                logger.warning(f"第{try_index}/{total_try_count}次尝试上传{local_filepath}失败，等待一会后重试")
                if try_index < total_try_count:
                    count_down("上传到网盘", 5 * try_index)
                    continue

            break

    # ---------------推送版本到github
    # 打包完成后git添加标签
    os.chdir(dir_src)
    show_head_line("开始推送到github", color("bold_yellow"))
    push_github(version)

    # ---------------查看github action
    show_head_line("为了保底，在github action同时打包发布一份，请在稍后打开的github action中查看打包结果", color("bold_yellow"))
    logger.info("等待两秒，确保action已开始处理，不必再手动刷新页面")
    time.sleep(2)
    webbrowser.open("https://github.com/fzls/djc_helper/actions/workflows/package.yml")

    # ---------------结束
    logger.info("+" * 40)
    logger.info(color("bold_yellow") + f"{version} 发布完成，共用时{datetime.now() - run_start_time}，请等待github action的构建打包流程完成")
    logger.info("+" * 40)

    os.system("PAUSE")


if __name__ == "__main__":
    release()

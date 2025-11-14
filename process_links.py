import os
import subprocess
import zipfile
import shutil
from pathlib import Path

def read_links(link_file: str) -> list[str]:
    """
    读取指定链接文件中的有效链接（过滤空行和注释行）。
    """
    if not os.path.exists(link_file):
        print(f"信息：{link_file} 文件不存在，将跳过读取。")
        return []
    
    with open(link_file, "r", encoding="utf-8") as f:
        links = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith("#")  # 跳过注释和空行
        ]
    print(f"从 {link_file} 成功读取 {len(links)} 个有效链接")
    return links

def get_current_files(dir_path: str) -> set[str]:
    """获取指定目录下所有文件/目录的绝对路径（用于对比下载前后差异）"""
    return set(
        str(path.resolve()) 
        for path in Path(dir_path).rglob("*")  # 递归获取所有子项
    )

def download_link(link: str, skip_attachments: bool, base_dir: str = "./download_base") -> list[str]:
    """
    下载单个链接的内容，返回新增的文件/目录路径列表。
    可根据 skip_attachments 参数决定是否跳过附件下载。
    """
    # 记录下载前的文件列表
    before_download = get_current_files(base_dir)
    
    try:
        # 根据是否跳过附件，构建不同的命令和提示信息
        if skip_attachments:
            print(f"\n=== 开始下载链接 (跳过附件): {link} ===")
            command = [
                "kemono-dl",
                link,
                "--path", base_dir,
                "--output", "{post_title}/{filename}",
                "--no-tmp",
                "--skip-extensions",  # 新增的参数
                "zip,rar"
            ]
        else:
            print(f"\n=== 开始下载链接: {link} ===")
            command = [
                "kemono-dl",
                link,
                "--path", base_dir,
                "--output", "{post_title}/{filename}",
                "--no-tmp"
            ]
            
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # 下载失败时抛出异常
            encoding='utf-8'
        )
        print(f"下载成功: {link}")
        
        # 对比下载前后的文件列表，获取新增内容
        after_download = get_current_files(base_dir)
        new_items = list(after_download - before_download)
        print(f"该链接新增 {len(new_items)} 个文件/目录")
        return new_items
    
    except subprocess.CalledProcessError as e:
        print(f"下载失败: {link}")
        print(f"错误信息: {e.stderr}")
        return []

def create_bundle(items: list[str], bundle_num: int, output_dir: str = "./bundles") -> bool:
    """
    将指定的文件/目录打包为 ZIP 压缩包
    items: 要打包的文件/目录路径列表
    bundle_num: 压缩包编号（用于命名）
    """
    if not items:
        print(f"警告：第 {bundle_num} 个压缩包无内容，跳过打包")
        return False
    
    # 过滤掉被包含在其他目录中的子项
    item_set = set(items)
    top_level_items = [
        item for item in items 
        if str(Path(item).parent) not in item_set
    ]
    print(f"过滤后，顶层项目数：{len(top_level_items)}")

    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, f"bundle-{bundle_num:03d}.zip")
    
    try:
        # 使用过滤后的 top_level_items进行打包
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            for item in top_level_items:
                if os.path.isfile(item):
                    rel_path = os.path.relpath(item, start="./download_base")
                    zipf.write(item, rel_path)
                elif os.path.isdir(item):
                    for root, _, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_rel_path = os.path.relpath(file_path, start="./download_base")
                            zipf.write(file_path, file_rel_path)
        
        print(f"✅ 成功创建压缩包: {zip_path} (包含 {len(top_level_items)} 个顶层项目)")
        return True
    
    except Exception as e:
        print(f"❌ 打包失败: {str(e)}")
        return False

def main():
    # 1. 读取两种链接文件
    
    normal_links = read_links("links.txt") if True else []
    skip_links = read_links("skip_links.txt") if True else []

    # 将所有链接统一到一个列表中，并标记是否需要跳过附件
    all_links = []
    for link in normal_links:
        all_links.append({"url": link, "skip": False})
    for link in skip_links:
        all_links.append({"url": link, "skip": True})

    if not all_links:
        print("未找到任何有效链接，程序退出。")
        return
    
    # 2. 初始化变量
    batch_size = 10
    current_batch = 1
    batch_items = []
    total_downloaded = 0
    
    # 3. 逐个处理所有链接
    for idx, link_info in enumerate(all_links, 1):
        link = link_info["url"]
        skip = link_info["skip"]
        
        new_items = download_link(link, skip_attachments=skip)
        
        # 过滤新增项目，只保留顶层路径
        item_set = set(new_items)
        top_level_new_items = [
            item for item in new_items
            if str(Path(item).parent) not in item_set
        ]

        if top_level_new_items:
            batch_items.extend(top_level_new_items)
            total_downloaded += 1
        
        # 4. 达到批次大小或处理完所有链接时，打包
        if len(batch_items) >= batch_size or idx == len(all_links):
            if batch_items:
                create_bundle(batch_items, current_batch)
                batch_items = []
                current_batch += 1
    
    # 5. 输出最终统计
    print(f"\n=== 处理完成 ===")
    print(f"总链接数: {len(all_links)}")
    print(f"成功下载数: {total_downloaded}")
    print(f"生成压缩包数: {current_batch - 1}")

if __name__ == "__main__":
    main()
import os
import subprocess
import zipfile
import shutil
from pathlib import Path

def read_links(link_file: str = "links.txt") -> list[str]:
    """读取 links.txt 中的有效链接（过滤空行和注释行）"""
    if not os.path.exists(link_file):
        print(f"错误：{link_file} 文件不存在！")
        return []
    
    with open(link_file, "r", encoding="utf-8") as f:
        links = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith("#")  # 跳过注释和空行
        ]
    print(f"成功读取 {len(links)} 个有效链接")
    return links

def get_current_files(dir_path: str) -> set[str]:
    """获取指定目录下所有文件/目录的绝对路径（用于对比下载前后差异）"""
    return set(
        str(path.resolve()) 
        for path in Path(dir_path).rglob("*")  # 递归获取所有子项
    )

def download_link(link: str, base_dir: str = "./download_base") -> list[str]:
    """
    下载单个链接的内容，返回新增的文件/目录路径列表
    使用 --path 指定基础路径，--output 简化目录结构
    """
    # 记录下载前的文件列表
    before_download = get_current_files(base_dir)
    
    try:
        print(f"\n=== 开始下载链接：{link} ===")
        # 核心命令：简化目录为「base_dir/帖子ID/文件名」
        result = subprocess.run(
            [
                "kemono-dl",
                link,
                "--path", base_dir,  # 基础下载路径
                "--output", "{post_title}/{filename}",  # 简化输出模板（仅保留帖子ID和文件名）
                "--no-tmp"  # 不生成临时文件，直接写入最终文件（避免捕获临时文件）
            ],
            capture_output=True,
            text=True,
            check=True  # 下载失败时抛出异常
        )
        print(f"下载成功：{link}")
        
        # 对比下载前后的文件列表，获取新增内容
        after_download = get_current_files(base_dir)
        new_items = list(after_download - before_download)
        print(f"该链接新增 {len(new_items)} 个文件/目录")
        return new_items
    
    except subprocess.CalledProcessError as e:
        print(f"下载失败：{link}")
        print(f"错误信息：{e.stderr}")
        return []

# def create_bundle(items: list[str], bundle_num: int, output_dir: str = "./bundles") -> bool:
#     """
#     将指定的文件/目录打包为 ZIP 压缩包
#     items: 要打包的文件/目录路径列表
#     bundle_num: 压缩包编号（用于命名）
#     """
#     if not items:
#         print(f"警告：第 {bundle_num} 个压缩包无内容，跳过打包")
#         return False
    
#     # 创建输出目录（若不存在）
#     os.makedirs(output_dir, exist_ok=True)
#     zip_path = os.path.join(output_dir, f"bundle-{bundle_num:03d}.zip")  # 命名格式：bundle-001.zip
    
#     try:
#         # with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
#         #     for item in items:
#         #         # 获取相对路径（以 download_base 为根目录，避免压缩包内包含完整系统路径）
#         #         rel_path = os.path.relpath(item, start="./download_base")
#         #         # 向压缩包添加文件/目录
#         #         if os.path.isfile(item):
#         #             zipf.write(item, rel_path)
#         #         elif os.path.isdir(item):
#         #             # 递归添加目录下所有内容
#         #             for root, _, files in os.walk(item):
#         #                 for file in files:
#         #                     file_path = os.path.join(root, file)
#         #                     file_rel_path = os.path.relpath(file_path, start="./download_base")
#         #                     zipf.write(file_path, file_rel_path)
#         with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
#             for item in items:
#                 if os.path.isfile(item):
#                     rel_path = os.path.relpath(item, start="./download_base")
#                     zipf.write(item, rel_path)
#                 elif os.path.isdir(item):
#                     for root, _, files in os.walk(item):
#                         for file in files:
#                             file_path = os.path.join(root, file)
#                             file_rel_path = os.path.relpath(file_path, start="./download_base")
#                             zipf.write(file_path, file_rel_path)
        
#         print(f"✅ 成功创建压缩包：{zip_path}（包含 {len(items)} 个项目）")
#         return True
    
#     except Exception as e:
#         print(f"❌ 打包失败：{str(e)}")
#         return False
def create_bundle(items: list[str], bundle_num: int, output_dir: str = "./bundles") -> bool:
    """
    将指定的文件/目录打包为 ZIP 压缩包
    items: 要打包的文件/目录路径列表
    bundle_num: 压缩包编号（用于命名）
    """
    if not items:
        print(f"警告：第 {bundle_num} 个压缩包无内容，跳过打包")
        return False
    
    # --- 新增代码：过滤掉被包含在其他目录中的子项 ---
    # 创建一个集合用于快速查找
    item_set = set(items)
    # 只保留那些其父目录不在待打包列表中的项目
    top_level_items = [
        item for item in items 
        if str(Path(item).parent) not in item_set
    ]
    print(f"过滤后，顶层项目数：{len(top_level_items)}")
    # ---------------------------------------------------

    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, f"bundle-{bundle_num:03d}.zip")
    
    try:
        # 使用过滤后的 top_level_items进行打包
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            for item in top_level_items: # <--- 注意：这里使用过滤后的列表
                if os.path.isfile(item):
                    rel_path = os.path.relpath(item, start="./download_base")
                    zipf.write(item, rel_path)
                elif os.path.isdir(item):
                    for root, _, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_rel_path = os.path.relpath(file_path, start="./download_base")
                            zipf.write(file_path, file_rel_path)
        
        print(f"✅ 成功创建压缩包：{zip_path}（包含 {len(top_level_items)} 个顶层项目）")
        return True
    
    except Exception as e:
        print(f"❌ 打包失败：{str(e)}")
        return False

def main():
    # 1. 读取链接
    links = read_links()
    if not links:
        return
    
    # 2. 初始化变量
    batch_size = 10  # 每 10 个链接打包一次
    current_batch = 1  # 当前批次编号
    batch_items = []   # 当前批次的所有下载内容
    total_downloaded = 0  # 总下载成功的链接数
    
    # 3. 逐个处理链接
    for idx, link in enumerate(links, 1):
        new_items = download_link(link)
        if new_items:
            batch_items.extend(new_items)
            total_downloaded += 1
        
        # 4. 达到批次大小或处理完所有链接时，打包
        if len(batch_items) >= batch_size or idx == len(links):
            if batch_items:  # 仅当有内容时打包
                create_bundle(batch_items, current_batch)
                # 重置批次变量
                batch_items = []
                current_batch += 1
    
    # 5. 输出最终统计
    print(f"\n=== 处理完成 ===")
    print(f"总链接数：{len(links)}")
    print(f"成功下载数：{total_downloaded}")
    print(f"生成压缩包数：{current_batch - 1}")

if __name__ == "__main__":
    main()
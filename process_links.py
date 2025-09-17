import os
import subprocess
import zipfile
import shutil
from pathlib import Path
from typing import List, Set

def read_links(link_file: str = "links.txt") -> List[str]:
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

def get_current_items(dir_path: str) -> Set[str]:
    """获取指定目录下所有文件/目录的绝对路径（仅保留存在的项，避免已删除项干扰）"""
    current_items = set()
    for path in Path(dir_path).rglob("*"):
        abs_path = str(path.resolve())
        if os.path.exists(abs_path):  # 仅保留当前存在的项（排除已删除文件）
            current_items.add(abs_path)
    return current_items

def extract_post_id(link: str) -> str:
    """从链接中提取 post_id（用于临时目录命名，避免跨链接文件冲突）"""
    # 支持 kemono/coomer 的链接格式：https://xxx.com/xxx/user/xxx/post/POST_ID
    if "/post/" in link:
        post_id = link.split("/post/")[-1].split("?")[0]  # 排除 URL 参数
        return post_id.strip()
    # 若无法提取 post_id，使用随机字符串（避免目录重名）
    import uuid
    return str(uuid.uuid4())[:8]

def download_link(link: str, base_dir: str = "./download_base") -> List[str]:
    """
    下载单个链接的内容，返回新增的文件路径列表
    优化点：
    1. 为每个链接创建独立的临时目录（post_id 命名），避免跨链接文件冲突
    2. 下载后仅保留文件（删除空目录），减少无效路径
    3. 捕获真实下载的文件路径（排除目录）
    """
    # 1. 为当前链接创建独立临时目录（避免与其他链接的文件混淆）
    post_id = extract_post_id(link)
    link_temp_dir = os.path.join(base_dir, post_id)
    os.makedirs(link_temp_dir, exist_ok=True)
    
    # 2. 记录下载前的文件列表（仅文件，排除目录）
    def get_files_only(items: Set[str]) -> Set[str]:
        return {item for item in items if os.path.isfile(item)}
    
    before_files = get_files_only(get_current_items(base_dir))
    
    try:
        print(f"\n=== 开始下载链接：{link} ===")
        print(f"临时目录：{link_temp_dir}")
        
        # 核心下载命令：文件直接保存到「base_dir/post_id/文件名」
        result = subprocess.run(
            [
                "kemono-dl",
                link,
                "--path", base_dir,  # 基础路径
                "--output", f"{post_id}/{filename}",  # 每个链接的文件独立存放在 post_id 目录
                "--no-tmp",  # 不生成临时文件，避免捕获无效路径
                "--skip-attachments",  # 可选：跳过附件（根据需求决定是否保留）
            ],
            capture_output=True,
            text=True,
            check=True  # 下载失败时抛出异常
        )
        
        # 3. 记录下载后的文件列表（仅文件）
        after_files = get_files_only(get_current_items(base_dir))
        new_files = list(after_files - before_files)
        
        # 4. 清理空目录（避免空文件夹被加入压缩包）
        for dir_path in Path(base_dir).rglob("*"):
            if dir_path.is_dir() and not any(dir_path.iterdir()):  # 空目录
                os.rmdir(dir_path)
                print(f"清理空目录：{dir_path}")
        
        print(f"该链接成功下载 {len(new_files)} 个文件")
        return new_files
    
    except subprocess.CalledProcessError as e:
        print(f"下载失败：{link}")
        print(f"错误信息：{e.stderr.strip() or e.stdout.strip()}")
        # 下载失败时删除临时目录（避免空目录残留）
        if os.path.exists(link_temp_dir) and not any(Path(link_temp_dir).iterdir()):
            os.rmdir(link_temp_dir)
            print(f"删除空临时目录：{link_temp_dir}")
        return []
    except Exception as e:
        print(f"下载过程异常：{str(e)}")
        # 异常时清理临时目录
        if os.path.exists(link_temp_dir) and not any(Path(link_temp_dir).iterdir()):
            os.rmdir(link_temp_dir)
        return []

def create_bundle(items: List[str], bundle_num: int, output_dir: str = "./bundles") -> bool:
    """
    将指定文件打包为 ZIP 压缩包（支持去重，避免重复文件路径）
    优化点：
    1. 对文件路径去重，避免重复添加同一文件
    2. 打包时使用相对路径，确保压缩包内目录结构清晰
    3. 跳过不存在的文件（避免打包失败）
    """
    if not items:
        print(f"警告：第 {bundle_num} 个压缩包无有效文件，跳过打包")
        return False
    
    # 1. 去重 + 过滤不存在的文件（关键修复：避免重复路径和无效文件）
    unique_items = list(set(items))  # 去重
    valid_items = [item for item in unique_items if os.path.exists(item) and os.path.isfile(item)]
    
    if not valid_items:
        print(f"警告：第 {bundle_num} 个压缩包无有效文件（已过滤重复/不存在项），跳过打包")
        return False
    
    # 2. 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, f"bundle-{bundle_num:03d}.zip")  # 格式化命名：bundle-001.zip
    
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            added_paths = set()  # 记录已添加到压缩包的相对路径（二次去重）
            base_dir = os.path.abspath("./download_base")  # 基础路径（用于计算相对路径）
            
            for file_path in valid_items:
                # 计算压缩包内的相对路径（避免完整系统路径）
                rel_path = os.path.relpath(file_path, base_dir)
                
                # 避免压缩包内出现重复路径（关键修复：同一压缩包内不允许重复文件名）
                if rel_path in added_paths:
                    print(f"跳过重复压缩路径：{rel_path}")
                    continue
                
                # 添加文件到压缩包
                zipf.write(file_path, rel_path)
                added_paths.add(rel_path)
                print(f"添加到压缩包：{rel_path}")
        
        print(f"✅ 成功创建压缩包：{zip_path}（包含 {len(added_paths)} 个文件）")
        # 打包后清理已打包的文件（避免下一批次重复打包）
        for file_path in valid_items:
            if os.path.exists(file_path):
                os.remove(file_path)
                # 清理空父目录（如 post_id 目录）
                parent_dir = os.path.dirname(file_path)
                if os.path.isdir(parent_dir) and not any(Path(parent_dir).iterdir()):
                    os.rmdir(parent_dir)
        return True
    
    except Exception as e:
        print(f"❌ 打包失败：{str(e)}")
        return False

def main():
    # 初始化配置
    base_download_dir = "./download_base"
    batch_size = 10  # 每 10 个链接打包一次
    current_batch = 1
    batch_files: List[str] = []  # 当前批次的文件列表（仅保留文件，排除目录）
    
    # 1. 初始化下载目录（清空旧目录，避免历史文件干扰）
    if os.path.exists(base_download_dir):
        shutil.rmtree(base_download_dir)
        print(f"清空历史下载目录：{base_download_dir}")
    os.makedirs(base_download_dir, exist_ok=True)
    
    # 2. 读取链接
    links = read_links()
    if not links:
        print("无有效链接，退出流程")
        return
    
    # 3. 逐个处理链接
    for link_idx, link in enumerate(links, 1):
        # 下载当前链接，获取新增文件列表
        new_files = download_link(link, base_download_dir)
        if new_files:
            batch_files.extend(new_files)
            print(f"当前批次已累计 {len(batch_files)} 个文件")
        
        # 4. 满足批次大小或处理完所有链接时，打包
        if len(batch_files) >= batch_size or link_idx == len(links):
            if batch_files:
                create_bundle(batch_files, current_batch)
                # 清空当前批次缓存（关键修复：避免批次间文件残留）
                batch_files = []
                current_batch += 1
            else:
                print(f"第 {current_batch} 批次无有效文件，跳过打包")
    
    # 5. 最终清理（删除空下载目录）
    if os.path.exists(base_download_dir) and not any(Path(base_download_dir).iterdir()):
        shutil.rmtree(base_download_dir)
        print(f"清理空下载目录：{base_download_dir}")
    
    print(f"\n=== 流程结束 ===")
    print(f"总处理链接数：{len(links)}")
    print(f"总生成压缩包数：{current_batch - 1}")

if __name__ == "__main__":
    main()
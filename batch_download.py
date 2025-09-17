import os
import subprocess
import zipfile
import time
import shutil
from pathlib import Path

# 配置参数
LINKS_FILE = "links.txt"
BUNDLE_DIR = "bundles"
TEMP_DIR = "temp_downloads"
BUNDLE_SIZE = 10  # 每个压缩包包含的链接数量

def run_command(link):
    """执行下载命令并返回是否成功"""
    try:
        result = subprocess.run(
            ["kemono-dl", link],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ 成功下载: {link}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 下载失败: {link}")
        print(f"错误信息: {e.stderr}")
        return False

def create_bundle(bundle_id, links):
    """创建压缩包并返回文件路径"""
    os.makedirs(BUNDLE_DIR, exist_ok=True)
    bundle_name = f"bundle-{bundle_id:03d}.zip"
    bundle_path = os.path.join(BUNDLE_DIR, bundle_name)
    
    print(f"📦 正在创建压缩包: {bundle_name}")
    
    with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for link in links:
            # 获取链接对应的用户ID（用于组织目录）
            user_id = link.split('/')[-3]
            user_dir = os.path.join(TEMP_DIR, user_id)
            
            if os.path.exists(user_dir):
                # 添加用户目录下的所有文件
                for root, _, files in os.walk(user_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, TEMP_DIR)
                        zipf.write(file_path, arcname)
                # 清理已打包的文件
                shutil.rmtree(user_dir)
    
    return bundle_path

def main():
    # 准备临时目录
    Path(TEMP_DIR).mkdir(exist_ok=True)
    
    # 读取链接文件
    if not os.path.exists(LINKS_FILE):
        print(f"⚠️ 链接文件 {LINKS_FILE} 不存在")
        return
    
    with open(LINKS_FILE, 'r') as f:
        links = [line.strip() for line in f.readlines() if line.strip()]
    
    if not links:
        print("ℹ️ 链接文件为空")
        return
    
    print(f"🔗 找到 {len(links)} 个链接")
    
    # 分批处理链接
    bundle_id = 0
    current_bundle_links = []
    
    for i, link in enumerate(links):
        print(f"\n🔍 处理链接 ({i+1}/{len(links)}): {link}")
        
        # 在临时目录中执行下载
        os.chdir(TEMP_DIR)
        success = run_command(link)
        os.chdir("..")
        
        if success:
            current_bundle_links.append(link)
            
            # 每10个成功链接打包一次
            if len(current_bundle_links) >= BUNDLE_SIZE:
                create_bundle(bundle_id, current_bundle_links)
                bundle_id += 1
                current_bundle_links = []
    
    # 处理剩余的链接
    if current_bundle_links:
        create_bundle(bundle_id, current_bundle_links)
    
    print("\n🎉 所有链接处理完成！")

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"⏱️ 总耗时: {time.time() - start_time:.2f}秒")
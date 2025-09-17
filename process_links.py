import os
import subprocess
import zipfile
from glob import glob
import shutil

def read_links(filename):
    """读取links.txt文件中的所有链接"""
    with open(filename, 'r', encoding='utf-8') as f:
        # 过滤空行和注释行
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def download_with_kemono_dl(url, output_dir):
    """使用kemono-dl下载指定链接的内容"""
    try:
        print(f"开始下载: {url}")
        # 运行kemono-dl命令，指定输出目录
        result = subprocess.run(
            ['kemono-dl', url, '-o', output_dir],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"成功下载: {url}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"下载失败 {url}: {e.stderr}")
        return False

def create_zip(contents, zip_filename):
    """将指定文件和目录压缩到ZIP文件"""
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in contents:
            if os.path.isfile(item):
                # 添加文件，保留相对路径
                zipf.write(item, os.path.relpath(item, 'downloads'))
            elif os.path.isdir(item):
                # 添加目录及其内容
                for root, _, files in os.walk(item):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, 'downloads')
                        zipf.write(file_path, arcname)

def main():
    # 读取所有链接
    links = read_links('links.txt')
    if not links:
        print("没有找到有效的链接")
        return

    # 下载计数器
    download_count = 0
    # 每批处理的链接数量
    batch_size = 10
    # 当前批次
    current_batch = 1
    # 当前批次下载的内容列表
    batch_contents = []

    # 确保下载目录存在
    os.makedirs('downloads', exist_ok=True)
    os.makedirs('bundles', exist_ok=True)

    for link in links:
        # 下载链接内容
        success = download_with_kemono_dl(link, 'downloads')
        if success:
            download_count += 1
            
            # 获取刚刚下载的内容（假设最后修改的项目是新下载的）
            # 这是一个简化的方法，可能需要根据实际情况调整
            all_items = glob(os.path.join('downloads', '*'))
            all_items.sort(key=os.path.getmtime, reverse=True)
            
            if all_items:
                batch_contents.append(all_items[0])
            
            # 每达到batch_size个链接，打包一次
            if download_count % batch_size == 0:
                zip_name = f"bundles/bundle-{current_batch}.zip"
                print(f"创建压缩包: {zip_name}")
                create_zip(batch_contents, zip_name)
                
                # 重置批次变量
                current_batch += 1
                batch_contents = []

    # 处理剩余的未打包内容
    if batch_contents:
        zip_name = f"bundles/bundle-{current_batch}.zip"
        print(f"创建压缩包: {zip_name}")
        create_zip(batch_contents, zip_name)

    print(f"处理完成。共下载 {download_count} 个链接，生成 {current_batch} 个压缩包。")

if __name__ == "__main__":
    main()

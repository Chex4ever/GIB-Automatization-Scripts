import os, shutil, pathlib, requests, re, zipfile
from tqdm import tqdm
def download_latest_windows_yandexdriver():
    print("Searching for the latest YandexDriver Windows binary...")
    
    # Get all releases (not just the latest)
    api_url = "https://api.github.com/repos/yandex/YandexDriver/releases"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        releases = response.json()
        
        if not releases:
            print("No releases found.")
            return
            
        print(f"Found {len(releases)} releases. Searching for Windows binaries...")
        
        # Windows binary patterns
        win_patterns = [
            r'yandexdriver-.*-win\d+\.zip',
            r'yandexdriver-.*-windows\d*\.zip',
            r'yandexdriver.*win\d+\.zip',
            r'.*windows.*\.zip',
            r'.*win\d+.*\.zip'
        ]
        
        for release in releases:
            version = release.get('tag_name', 'Unknown')
            published_date = release.get('published_at', 'Unknown date')
            assets = release.get('assets', [])
            
            for asset in assets:
                asset_name = asset['name'].lower()
                
                # Check if this asset matches any Windows pattern
                is_windows_binary = any(re.match(pattern, asset_name, re.IGNORECASE) for pattern in win_patterns)
                
                if is_windows_binary:
                    print(f"\nFound Windows binary in release {version} (published: {published_date})")
                    print(f"Binary: {asset['name']} ({asset['size']/1024/1024:.2f} MB)")
                    
                    # Download the binary
                    download_url = asset['browser_download_url']
                    filename = asset['name']
                    file_size = asset['size']
                    
                    print(f"Downloading {filename}...")
                    
                    # Stream download with progress bar
                    dl_response = requests.get(download_url, stream=True)
                    dl_response.raise_for_status()
                    
                    with open(filename, 'wb') as f:
                        with tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                            for chunk in dl_response.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    f.write(chunk)
                                    pbar.update(len(chunk))
                    
                    print(f"Successfully downloaded {filename} to {os.getcwd()}")
                    return filename
        
        print("\nNo Windows binaries found in any release.")
        return False
                
    except requests.exceptions.RequestException as e:
        print(f"Error fetching releases: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        
    return False

def extract_zip(zip_file):
    """Extract all contents of the zip file to the current directory"""
    try:
        print(f"Extracting {zip_file} to current directory...")
        
        # Create a temporary directory for extraction
        temp_dir = "temp_extract"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # Extract to temp directory first
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            print(f"Found {total_files} files in archive")
            
            # Extract all files with progress bar
            for i, file in enumerate(zip_ref.infolist()):
                zip_ref.extract(file, temp_dir)
                print(f"Extracted: {file.filename} ({i+1}/{total_files})")
        
        # Move all files from temp directory to current directory
        extracted_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                src_path = os.path.join(root, file)
                # Get the path relative to the temp directory
                rel_path = os.path.relpath(src_path, temp_dir)
                dst_path = os.path.join(os.getcwd(), rel_path)
                
                # Create directories if needed
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # Move the file
                shutil.move(src_path, dst_path)
                extracted_files.append(rel_path)
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        print(f"Successfully extracted {len(extracted_files)} files to {os.getcwd()}")
        print("Extracted files:")
        for file in extracted_files:
            print(f"  - {file}")
            
        return True
        
    except Exception as e:
        print(f"Error extracting zip file: {e}")
        return False

def check_github_release(owner, repo, version_file, download_dir=None):
    """
    Check for new releases of a GitHub repository.
    
    Args:
        owner (str): GitHub repository owner
        repo (str): GitHub repository name
        version_file (str): Path to file storing the current version
        download_dir (str, optional): Directory to save downloads. Defaults to None.
    
    Returns:
        bool: True if a new version was found, False otherwise
    """
    # GitHub API URL for latest release
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    
    # Get the current stored version
    current_version = None
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            current_version = f.read().strip()
        print(f"Current version: {current_version}")
    else:
        print("No stored version found")
    
    # Get the latest release info from GitHub
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        release_data = response.json()
        latest_version = release_data["tag_name"]
        print(f"Latest version: {latest_version}")
        
        # Compare versions
        if current_version != latest_version:
            print(f"New version found: {latest_version}")
            
            # Save the new version
            with open(version_file, 'w') as f:
                f.write(latest_version)
            
            # Download the release if download_dir is specified
            if download_dir:
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)
                
                # Get the first asset (you might want to modify this to select a specific asset)
                if release_data["assets"]:
                    asset = release_data["assets"][0]
                    download_url = asset["browser_download_url"]
                    filename = os.path.join(download_dir, asset["name"])
                    
                    print(f"Downloading {download_url} to {filename}")
                    download_response = requests.get(download_url, stream=True)
                    download_response.raise_for_status()
                    
                    with open(filename, 'wb') as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"Download complete: {filename}")
                else:
                    print("No assets found in the release")
            
            return True
        else:
            print("Already at the latest version, skipping download")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error checking for updates: {e}")
        return False

def yandexdriver_update():
    print('current dir:',pathlib.Path().resolve())
    if check_github_release('yandex', 'YandexDriver', 'current_version.txt', ''):
        filename=download_latest_windows_yandexdriver()
        if filename.lower().endswith('.zip'):
            if extract_zip(filename):
                os.remove(filename)
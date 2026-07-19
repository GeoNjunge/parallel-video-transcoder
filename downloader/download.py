import subprocess
import os
import re
import time
import json
from pathlib import Path
from difflib import SequenceMatcher

# Supported platforms with their search prefixes
PLATFORMS = {
    'youtube': 'ytsearch',
    'youtube_music': 'ytmsearch',
    'soundcloud': 'scsearch',
    'bandcamp': 'bcsearch',
    'mixcloud': 'mcsearch',
    'audiomack': 'amsearch',
}

def read_tracklist(file_path):
    """Read tracklist from text file"""
    tracks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Remove track numbers if present
                    cleaned = re.sub(r'^\d+[\.\s-]+', '', line)
                    tracks.append(cleaned)
        return tracks
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
        return None

def search_platform(query, platform='youtube', max_results=10):
    """Search on a specific platform using yt-dlp"""
    search_prefix = PLATFORMS.get(platform, 'ytsearch')
    search_cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        f"{search_prefix}{max_results}:{query}"
    ]
    
    try:
        result = subprocess.run(search_cmd, capture_output=True, text=True, check=True)
        videos = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    # Get the actual URL
                    video_url = f"https://youtube.com/watch?v={data['id']}" if platform in ['youtube', 'youtube_music'] else data.get('url', '')
                    if not video_url:
                        # Try to get URL from webpage_url
                        video_url = data.get('webpage_url', data.get('url', ''))
                    
                    videos.append({
                        'url': video_url,
                        'title': data.get('title', 'Unknown'),
                        'duration': data.get('duration', 0),
                        'uploader': data.get('uploader', data.get('channel', 'Unknown')),
                        'platform': platform,
                        'webpage_url': data.get('webpage_url', '')
                    })
                except json.JSONDecodeError:
                    continue
        return videos
    except subprocess.CalledProcessError as e:
        # Ignore search errors for platforms that might not work
        return []

def extract_keywords(text):
    """Extract meaningful keywords from text"""
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                  'official', 'video', 'audio', 'music', 'lyric', 'hd', '4k', 'full', 'song', 'remix', 
                  'cover', 'live', 'performance', 'feat', 'ft', 'featuring', 'exclusive', 'premiere'}
    
    words = re.findall(r'[a-z0-9]+', text.lower())
    keywords = [w for w in words if len(w) > 2 and w not in stop_words]
    return keywords

def calculate_match_score(search_terms, video_title):
    """Calculate how well a video title matches search terms"""
    search_keywords = extract_keywords(search_terms)
    title_keywords = extract_keywords(video_title)
    
    if not search_keywords:
        return 0
    
    # Check for exact matches (case insensitive)
    exact_matches = 0
    for keyword in search_keywords:
        if keyword in video_title.lower():
            exact_matches += 1
    
    # Check for partial matches (word contains search term)
    partial_matches = 0
    for keyword in search_keywords:
        for title_word in title_keywords:
            if keyword in title_word or title_word in keyword:
                partial_matches += 1
                break
    
    # Calculate score based on matches
    score = (exact_matches * 1.5 + partial_matches * 0.5) / len(search_keywords) if search_keywords else 0
    
    return min(score, 1.0)  # Cap at 1.0

def filter_matching_videos(videos, search_terms, min_score=0.5):
    """Filter videos that match search terms"""
    matching = []
    for video in videos:
        is_match_result, score = is_match(search_terms, video['title'], min_score)
        if is_match_result:
            matching.append({
                **video,
                'match_score': score
            })
    
    # Sort by match score (highest first)
    matching.sort(key=lambda x: x['match_score'], reverse=True)
    return matching

def is_match(search_terms, video_title, min_score=0.5):
    """Check if video title matches search terms"""
    score = calculate_match_score(search_terms, video_title)
    return score >= min_score, score

def search_all_platforms(track_name, artist_name, min_score=0.5, max_results=10, quiet=False):
    """Search across all available platforms"""
    search_query = f"{track_name} {artist_name}"
    all_results = []
    
    platforms_to_try = ['youtube', 'youtube_music', 'soundcloud', 'mixcloud']
    
    for platform in platforms_to_try:
        if not quiet:
            print(f"    Searching {platform}...")
        results = search_platform(search_query, platform, max_results)
        
        if results:
            # Filter matches
            matching = filter_matching_videos(results, f"{track_name} {artist_name}", min_score)
            if matching:
                all_results.extend(matching)
                if not quiet:
                    print(f"    Found {len(matching)} matches on {platform}")
                    # Show best match from this platform
                    best = matching[0]
                    print(f"      Best: {best['title'][:50]}... (Score: {int(best['match_score']*100)}%)")
            else:
                if not quiet:
                    print(f"    No matches found on {platform}")
        else:
            if not quiet:
                print(f"    No results from {platform}")
        
        # Small delay between platform searches
        time.sleep(0.5)
    
    # Sort all results by score
    all_results.sort(key=lambda x: x['match_score'], reverse=True)
    return all_results

def format_duration(seconds):
    """Format duration in seconds to MM:SS or HH:MM:SS"""
    if not seconds:
        return "Unknown"
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def download_video(video_url, output_path, quality="480p"):
    """Download video using yt-dlp"""
    format_spec = get_format_spec(quality)
    
    download_cmd = [
        "yt-dlp",
        "--format", format_spec,
        "--merge-output-format", "mp4",
        "--output", output_path,
        "--external-downloader", "aria2c",
        "--external-downloader-args", "-c -j 16 -x 16 -s 16 -k 1M",
        "--no-playlist",
        "--progress",
        video_url
    ]
    
    try:
        subprocess.run(download_cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Download error: {e}")
        return False

def get_format_spec(quality):
    """Get yt-dlp format specification"""
    quality = str(quality).lower().strip()
    
    if quality == "audio":
        return "bestaudio/best"
    
    try:
        height = int(re.search(r'(\d+)', quality).group(1))
    except:
        height = 480
    
    if height >= 1080:
        return "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"
    elif height >= 720:
        return "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"
    elif height >= 480:
        return "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best"
    elif height >= 360:
        return "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best"
    else:
        return "best[ext=mp4]"

def select_video_batch(track_name, artist_name, videos, index, total):
    """Select a video from the list (batch mode)"""
    if not videos:
        return None
    
    print(f"\n{'='*60}")
    print(f"[{index}/{total}] {track_name}")
    print(f"{'='*60}")
    
    # Show top 5 results only to keep it manageable
    show_count = min(5, len(videos))
    print(f"  Found {len(videos)} matching videos (showing top {show_count}):")
    print()
    
    for i, video in enumerate(videos[:show_count], 1):
        duration = format_duration(video.get('duration', 0))
        score_percent = int(video.get('match_score', 0) * 100)
        platform = video.get('platform', 'unknown').upper()
        print(f"  {i}. [{platform}] {video.get('title', 'Unknown')[:70]}")
        print(f"     Uploader: {video.get('uploader', 'Unknown')} | Duration: {duration} | Match: {score_percent}%")
        print(f"     URL: {video.get('url', 'N/A')}")
        print()
    
    if len(videos) > show_count:
        print(f"  ... and {len(videos) - show_count} more results")
    
    while True:
        print("\n  Options:")
        print(f"  1-{show_count}: Select video by number")
        print("  n: Show next 5 results")
        print("  s: Skip this track")
        print("  a: Auto-select best match")
        
        choice = input("\n  Your choice: ").strip().lower()
        
        if choice == 's':
            return None
        elif choice == 'a':
            return videos[0]
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < min(show_count, len(videos)):
                return videos[idx]
        elif choice == 'n':
            # Show more results
            remaining = videos[show_count:]
            if remaining:
                for i, video in enumerate(remaining, show_count + 1):
                    duration = format_duration(video.get('duration', 0))
                    score_percent = int(video.get('match_score', 0) * 100)
                    platform = video.get('platform', 'unknown').upper()
                    print(f"  {i}. [{platform}] {video.get('title', 'Unknown')[:70]}")
                    print(f"     Uploader: {video.get('uploader', 'Unknown')} | Duration: {duration} | Match: {score_percent}%")
                    print(f"     URL: {video.get('url', 'N/A')}")
                    print()
                # Now let them select from all
                while True:
                    select_choice = input(f"\n  Select video (1-{len(videos)}) or s to skip: ").strip().lower()
                    if select_choice == 's':
                        return None
                    if select_choice.isdigit():
                        idx = int(select_choice) - 1
                        if 0 <= idx < len(videos):
                            return videos[idx]
                    print("  Invalid choice")
            else:
                print("  No more results")
        else:
            print("  Invalid choice. Please try again.")

def download_all_selected(selected_videos, album_dir, quality="480p"):
    """Download all selected videos in batch"""
    if not selected_videos:
        print("\n❌ No videos selected for download")
        return 0, []
    
    print("\n" + "=" * 60)
    print(f"📥 Starting batch download of {len(selected_videos)} tracks...")
    print("=" * 60)
    print()
    
    successful = 0
    failed = []
    
    for i, (track_name, video, output_path) in enumerate(selected_videos, 1):
        print(f"\n[{i}/{len(selected_videos)}] Downloading: {track_name}")
        print(f"  Source: {video.get('platform', 'unknown').upper()}")
        print(f"  Title: {video.get('title', 'Unknown')[:60]}...")
        
        if download_video(video.get('url', ''), output_path, quality):
            successful += 1
            print(f"  ✅ Downloaded")
        else:
            failed.append((track_name, video))
            print(f"  ❌ Failed")
        
        # Small delay between downloads
        time.sleep(1)
    
    return successful, failed

def download_album_from_tracklist(tracklist_file, artist_name="", quality="480p", interactive=True, min_match_score=0.5):
    """Main function to download album from tracklist"""
    
    # Read tracklist
    tracks = read_tracklist(tracklist_file)
    if not tracks:
        return
    
    # Get album name from file name
    album_name = Path(tracklist_file).stem
    if not artist_name:
        artist_name = input("Enter artist name: ").strip()
    
    # Create album folder
    safe_album_name = "".join(c for c in f"{album_name} - {artist_name}" if c.isalnum() or c in (' ', '-', '_')).rstrip()
    album_dir = os.path.join(".", safe_album_name)
    os.makedirs(album_dir, exist_ok=True)
    
    print(f"\n📁 Album: {album_name}")
    print(f"🎤 Artist: {artist_name}")
    print(f"📹 Quality: {quality}")
    print(f"📝 Tracks: {len(tracks)}")
    print(f"🎯 Minimum match score: {int(min_match_score*100)}%")
    print(f"🌐 Platforms: YouTube, YouTube Music, SoundCloud, Mixcloud")
    if interactive:
        print("🖱️  Mode: Interactive (you'll select each video)")
    else:
        print("🤖 Mode: Auto (best match for each track)")
    print("=" * 60)
    
    if interactive:
        # BATCH MODE: Select all first, then download
        print("\n🔍 Searching for tracks... (this may take a moment)")
        print("=" * 60)
        
        # First pass: Search and select all videos
        selected_videos = []
        skipped_tracks = []
        no_matches = []
        
        for i, track in enumerate(tracks, 1):
            print(f"\n[{i}/{len(tracks)}] Searching: {track}")
            
            # Clean filename
            safe_track = "".join(c for c in track if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            output_path = os.path.join(album_dir, f"{i:02d} - {safe_track}.%(ext)s")
            
            # Search all platforms
            all_results = search_all_platforms(track, artist_name, min_match_score, quiet=True)
            
            if not all_results:
                print(f"  ❌ No matching videos found")
                no_matches.append((i, track))
                continue
            
            # Let user select video
            selected = select_video_batch(track, artist_name, all_results, i, len(tracks))
            
            if selected:
                selected_videos.append((track, selected, output_path))
                print(f"  ✅ Selected: {selected.get('title', 'Unknown')[:60]}...")
            else:
                skipped_tracks.append((i, track))
                print(f"  ⏭️  Skipped")
        
        # Summary of selections
        print("\n" + "=" * 60)
        print("📋 Selection Summary")
        print("=" * 60)
        print(f"✅ Selected: {len(selected_videos)}/{len(tracks)}")
        print(f"⏭️  Skipped: {len(skipped_tracks)}")
        print(f"❌ No matches: {len(no_matches)}")
        
        if selected_videos:
            print("\nSelected tracks:")
            for i, (track, video, _) in enumerate(selected_videos, 1):
                platform = video.get('platform', 'unknown').upper()
                score = int(video.get('match_score', 0) * 100)
                print(f"  {i:02d}. {track[:40]}... [{platform}] (Match: {score}%)")
        
        # Ask for confirmation before downloading
        if selected_videos:
            print("\n" + "=" * 60)
            confirm = input("📥 Download all selected tracks? (y/n): ").strip().lower()
            
            if confirm == 'y':
                # Batch download all selected videos
                successful, failed = download_all_selected(selected_videos, album_dir, quality)
                
                print("\n" + "=" * 60)
                print(f"✅ Successfully downloaded: {successful}/{len(selected_videos)}")
                
                if failed:
                    print("\n❌ Failed downloads:")
                    for track, video in failed:
                        print(f"  - {track}")
                        if video.get('url'):
                            print(f"    URL: {video['url']}")
                    print(f"\nRetry these manually using the URLs above")
            else:
                print("\n⏹️  Download cancelled. Selected videos were not downloaded.")
                print("You can run the script again and re-select.")
        
        # Save selection info for later
        if selected_videos:
            selection_file = os.path.join(album_dir, "selected_tracks.txt")
            with open(selection_file, 'w') as f:
                f.write(f"Album: {album_name}\n")
                f.write(f"Artist: {artist_name}\n")
                f.write(f"Quality: {quality}\n")
                f.write("=" * 60 + "\n\n")
                f.write("Selected tracks:\n\n")
                for i, (track, video, output_path) in enumerate(selected_videos, 1):
                    f.write(f"{i:02d}. {track}\n")
                    f.write(f"   URL: {video.get('url', 'N/A')}\n")
                    f.write(f"   Platform: {video.get('platform', 'unknown').upper()}\n")
                    f.write(f"   Match Score: {int(video.get('match_score', 0)*100)}%\n\n")
            print(f"\nSelection info saved to: {selection_file}")
        
        # Save skipped and no-match tracks
        if skipped_tracks or no_matches:
            summary_file = os.path.join(album_dir, "unselected_tracks.txt")
            with open(summary_file, 'w') as f:
                f.write(f"Album: {album_name}\n")
                f.write(f"Artist: {artist_name}\n")
                f.write("=" * 60 + "\n\n")
                
                if skipped_tracks:
                    f.write("Skipped tracks:\n")
                    for num, track in skipped_tracks:
                        f.write(f"  {num:02d}. {track}\n")
                    f.write("\n")
                
                if no_matches:
                    f.write("No matches found:\n")
                    for num, track in no_matches:
                        f.write(f"  {num:02d}. {track}\n")
                    f.write("\nSearch suggestions:\n")
                    for num, track in no_matches:
                        f.write(f"  {num:02d}. {track} {artist_name}\n")
            print(f"Unselected tracks info saved to: {summary_file}")
    
    else:
        # AUTO MODE: Download immediately
        successful = 0
        failed_tracks = []
        
        for i, track in enumerate(tracks, 1):
            print(f"\n[{i}/{len(tracks)}] {track}")
            
            # Clean filename
            safe_track = "".join(c for c in track if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            output_path = os.path.join(album_dir, f"{i:02d} - {safe_track}.%(ext)s")
            
            # Search and download with auto-select
            all_results = search_all_platforms(track, artist_name, min_match_score)
            
            if all_results:
                # Auto-select the best match
                video = all_results[0]
                print(f"  Auto-selecting: {video['title'][:60]}... (Score: {int(video['match_score']*100)}%, Platform: {video.get('platform', 'unknown').upper()})")
                if download_video(video['url'], output_path, quality):
                    successful += 1
                    print(f"  ✅ Downloaded")
                else:
                    failed_tracks.append((i, track))
                    print(f"  ❌ Failed to download")
            else:
                failed_tracks.append((i, track))
                print(f"  ❌ No matching videos found")
            
            # Small delay to avoid rate limiting
            time.sleep(1)
        
        # Summary
        print("\n" + "=" * 60)
        print(f"✅ Successfully downloaded: {successful}/{len(tracks)}")
        
        if failed_tracks:
            print("\n❌ Failed tracks:")
            for num, track in failed_tracks:
                print(f"  {num:02d}. {track}")
            
            # Save failed tracks with more details
            failed_file = os.path.join(album_dir, "failed_tracks.txt")
            with open(failed_file, 'w') as f:
                for num, track in failed_tracks:
                    f.write(f"{num:02d}. {track}\n")
            print(f"\nFailed tracks saved to: {failed_file}")

def download_specific_track():
    """Download a single track with fallback"""
    track_name = input("Enter track name: ").strip()
    artist_name = input("Enter artist name: ").strip() or "Unknown"
    quality = input("Quality (480p/720p/1080p/audio) [480p]: ").strip() or "480p"
    min_score = float(input("Minimum match score (0.3-1.0) [0.5]: ").strip() or "0.5")
    
    # Search and select
    all_results = search_all_platforms(track_name, artist_name, min_score)
    
    if all_results:
        # Show all results for single track
        print(f"\n  Found {len(all_results)} matching videos:")
        for i, video in enumerate(all_results[:10], 1):
            duration = format_duration(video.get('duration', 0))
            score_percent = int(video.get('match_score', 0) * 100)
            platform = video.get('platform', 'unknown').upper()
            print(f"  {i}. [{platform}] {video.get('title', 'Unknown')[:70]}")
            print(f"     Uploader: {video.get('uploader', 'Unknown')} | Duration: {duration} | Match: {score_percent}%")
            print(f"     URL: {video.get('url', 'N/A')}")
        
        while True:
            choice = input(f"\n  Select video (1-{min(10, len(all_results))}) or 0 to skip: ").strip()
            if choice == "0":
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < min(10, len(all_results)):
                    selected = all_results[idx]
                    output_name = input("Output filename (press Enter for auto): ").strip()
                    if not output_name:
                        output_name = f"{track_name}.%(ext)s"
                    
                    confirm = input(f"Download '{selected.get('title', 'Unknown')[:60]}...'? (y/n): ").strip().lower()
                    if confirm == 'y':
                        print(f"\nDownloading...")
                        if download_video(selected.get('url', ''), output_name, quality):
                            print("✅ Download complete!")
                        else:
                            print("❌ Download failed")
                    return
            except ValueError:
                pass
            print("  Invalid choice. Please try again.")
    else:
        print("No matching videos found")

def create_tracklist_template():
    """Create a template tracklist file"""
    filename = "tracklist.txt"
    content = """# Album Tracklist
# Add one track per line
# Lines starting with # are ignored
# Example:

01. First Song Name
02. Second Song Name
03. Third Song Name
04. Fourth Song Name
05. Fifth Song Name
"""
    
    with open(filename, 'w') as f:
        f.write(content)
    print(f"✅ Created template: {filename}")
    print("Edit this file with your track names and run the script again.")

def test_platform_search():
    """Test search across platforms"""
    print("\n🔍 Test Platform Search")
    print("=" * 60)
    
    track = input("Enter track name: ").strip()
    artist = input("Enter artist name: ").strip()
    min_score = float(input("Minimum match score (0.3-1.0) [0.5]: ").strip() or "0.5")
    
    all_results = search_all_platforms(track, artist, min_score)
    
    if all_results:
        print(f"\n✅ Found {len(all_results)} matching results:")
        print("-" * 60)
        for i, result in enumerate(all_results[:10], 1):
            platform = result.get('platform', 'unknown').upper()
            score_percent = int(result.get('match_score', 0) * 100)
            duration = format_duration(result.get('duration', 0))
            print(f"{i}. [{platform}] {result.get('title', 'Unknown')[:70]}")
            print(f"   Score: {score_percent}% | Uploader: {result.get('uploader', 'Unknown')} | Duration: {duration}")
            print(f"   URL: {result.get('url', 'N/A')}")
            print()
    else:
        print("❌ No matching results found")

def main():
    print("=" * 60)
    print("🎵 Multi-Platform Album Downloader (Batch Mode)")
    print("=" * 60)
    print("\nOptions:")
    print("1. Download album (interactive - select all, then download)")
    print("2. Download album (auto - best match only)")
    print("3. Download single track")
    print("4. Create tracklist template")
    print("5. Test multi-platform search")
    print("0. Exit")
    
    choice = input("\nSelect option (0-5): ").strip()
    
    if choice == "0":
        return
    
    elif choice == "1":
        tracklist_file = input("Enter tracklist file path: ").strip()
        
        if not os.path.exists(tracklist_file):
            print(f"✗ File not found: {tracklist_file}")
            return
        
        artist_name = input("Enter artist name: ").strip()
        quality = input("Quality (360p/480p/720p/1080p/best/audio) [480p]: ").strip() or "480p"
        min_score = float(input("Minimum match score (0.3-1.0, higher = stricter) [0.5]: ").strip() or "0.5")
        
        download_album_from_tracklist(tracklist_file, artist_name, quality, interactive=True, min_match_score=min_score)
    
    elif choice == "2":
        tracklist_file = input("Enter tracklist file path: ").strip()
        
        if not os.path.exists(tracklist_file):
            print(f"✗ File not found: {tracklist_file}")
            return
        
        artist_name = input("Enter artist name: ").strip()
        quality = input("Quality (360p/480p/720p/1080p/best/audio) [480p]: ").strip() or "480p"
        min_score = float(input("Minimum match score (0.3-1.0, higher = stricter) [0.5]: ").strip() or "0.5")
        
        download_album_from_tracklist(tracklist_file, artist_name, quality, interactive=False, min_match_score=min_score)
    
    elif choice == "3":
        download_specific_track()
    
    elif choice == "4":
        create_tracklist_template()
    
    elif choice == "5":
        test_platform_search()
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Download cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
cat > polyrhythm.py << 'PY'
#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import argparse, sys, os, subprocess, shutil
from pydub import AudioSegment

DEFAULT_MAP = {2:"#C796AB",3:"#96C6AA",4:"#C77D88",5:"#9B9BD6",6:"#C8C792",7:"#6AB8D4",8:"#C8687E",9:"#7DC791",10:"#CB81D6",11:"#506FE2",12:"#C68F73",13:"#C8C77B",14:"#7A9AD6",15:"#81CBD6",16:"#C8596E"}

def darken_color(c,f=0.6):h=c.lstrip('#');r,g,b=tuple(int(h[i:i+2],16)for i in(0,2,4));dr,dg,db=tuple(max(0,int(c*f))for c in(r,g,b));return f"#{dr:02x}{dg:02x}{db:02x}"
def brighten_color(c,factor=0.4):h=c.lstrip('#');r,g,b=tuple(int(h[i:i+2],16)for i in(0,2,4));br,bg,bb=tuple(min(255,int(c+(255-c)*factor))for c in(r,g,b));return f"#{br:02x}{bg:02x}{bb:02x}"
def load_font(s):
    try:return ImageFont.truetype("fonts/Makinas-4-Square.otf",s)
    except:
        for f in["/system/fonts/HiraginoSans-W3.otf","/system/fonts/NotoSansCJK-Regular.ttc"]:
            try:
                if os.path.exists(f):return ImageFont.truetype(f,s)
            except:pass
    return ImageFont.load_default()
def text_size(d,t,f):
    if hasattr(d,"textbbox"):b=d.textbbox((0,0),t,f);return b[2]-b[0],b[3]-b[1]
    return d.textsize(t,f)

def parse_spec(spec):
    specs = []
    for part in spec.split(':'):
        part=part.strip().lower()
        if not part:continue
        is_off_beat=part.endswith('o');num_str=part.removesuffix('o')if is_off_beat else part
        if not num_str.isdigit():continue
        try:
            k=int(num_str)
            if k<2:continue
            color_key=k
            if k==1: color_key=16
            elif k>=17:color_key=((k-17)%15)+2
            color=DEFAULT_MAP.get(color_key,"#333333")
            specs.append({'k':k,'is_off_beat':is_off_beat,'label':part,'color':color})
        except ValueError:pass
    return specs

def make_audio_only(spec, out_path, bpm):
    print("音声のみの生成を開始します...")
    duration_sec = (60.0 / bpm) * 4.0; duration_ms = duration_sec * 1000
    print(f"BPM: {bpm}, 音声の長さ: {duration_sec:.2f}秒")
    
    sound_map = {}
    for i in range(2, 17):
        try: sound_map[i] = AudioSegment.from_file(f"sounds/{i}.mp3")
        except FileNotFoundError: print(f"エラー: 音源 'sounds/{i}.mp3' が見つかりません。"); sys.exit(1)

    try:
        start_sound = AudioSegment.from_file("sounds/start_sound.mp3")
    except FileNotFoundError:
        print("警告: 'sounds/start_sound.mp3' が見つかりません。開始音なしで生成します。")
        start_sound = None
            
    START_SOUND_DELAY_MS = 1000.0 / 15.0 
    
    final_audio = AudioSegment.silent(duration=duration_ms)
    
    if start_sound:
        # start_soundだけを、意図的に遅らせて配置する
        final_audio = final_audio.overlay(start_sound, position=START_SOUND_DELAY_MS)
    
    specs_data = parse_spec(spec)
    
    for s in specs_data:
        k = s['k']
        if k == 0: continue
        sound_key = k
        if k == 1: sound_key = 16
        elif k >= 17: sound_key = ((k - 17) % 15) + 2
        sound_to_use = sound_map.get(sound_key, sound_map[2])
        interval_sec = duration_sec / k
        for j in range(k + (0 if s['is_off_beat'] else 1)):
            time_offset_sec = (j + (0.5 if s['is_off_beat'] else 0.0)) * interval_sec
            time_offset_ms = time_offset_sec * 1000
            if time_offset_ms < duration_ms: final_audio = final_audio.overlay(sound_to_use, position=time_offset_ms)
            
    final_audio.export(out_path, format="mp3", bitrate="128k")
    print(f"音声ファイルを生成しました: {out_path}")

def make_video(spec, out_path, bpm, judge_window):
    print("動画生成を開始します..."); temp_dir = "temp_frames"
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    duration_sec = (60.0 / bpm) * 4.0; duration_ms = duration_sec * 1000
    print(f"BPM: {bpm}, 動画の長さ: {duration_sec:.2f}秒")
    
    sound_map = {};
    for i in range(2, 17):
        try: sound_map[i] = AudioSegment.from_file(f"sounds/{i}.mp3")
        except FileNotFoundError: print(f"エラー: 音源 'sounds/{i}.mp3' が見つかりません。"); shutil.rmtree(temp_dir); sys.exit(1)
    
    try:
        start_sound = AudioSegment.from_file("sounds/start_sound.mp3")
    except FileNotFoundError:
        print("警告: 'sounds/start_sound.mp3' が見つかりません。開始音なしで生成します。")
        start_sound = None

    START_SOUND_DELAY_MS = 1000.0 / 15.0

    final_audio = AudioSegment.silent(duration=duration_ms)

    if start_sound:
        # start_soundだけを、意図的に遅らせて配置する
        final_audio = final_audio.overlay(start_sound, position=START_SOUND_DELAY_MS)

    specs_data = parse_spec(spec); all_dot_timings = []
    for i, s in enumerate(specs_data):
        k = s['k'];
        if k == 0: continue
        sound_key = k;
        if k == 1: sound_key = 16
        elif k >= 17: sound_key = ((k - 17) % 15) + 2
        sound_to_use = sound_map.get(sound_key, sound_map[2]); interval_sec = duration_sec / k
        for j in range(k + (0 if s['is_off_beat'] else 1)):
            time_offset_sec = (j + (0.5 if s['is_off_beat'] else 0.0)) * interval_sec
            time_offset_ms = time_offset_sec * 1000
            if time_offset_ms < duration_ms: final_audio = final_audio.overlay(sound_to_use, position=time_offset_ms)
            dot_x = 140 + (1000 * (time_offset_sec / duration_sec)); dot_y = 100 + i * 120
            all_dot_timings.append({'time': time_offset_sec, 'x': dot_x, 'y': dot_y, 'color': s['color']})
            
    sound_path = os.path.join(temp_dir, "sound.wav"); final_audio.export(sound_path, format="wav"); print(f"音声ファイルを生成しました: {sound_path}")
    base_img = make_base_image(spec, judge_window, specs_data, bpm); fps = 30; total_frames = int(duration_sec * fps)
    
    for i in range(total_frames):
        frame_img = base_img.copy(); draw = ImageDraw.Draw(frame_img, "RGBA"); current_time = i / fps
        highlight_duration = 0.15
        for dot in all_dot_timings:
            time_diff = current_time - dot['time']
            if 0 <= time_diff < highlight_duration:
                brightness = 1.0 - (time_diff / highlight_duration); highlight_color = brighten_color(dot['color'], factor=0.8)
                r,g,b = tuple(int(highlight_color.lstrip('#')[c:c+2], 16) for c in (0, 2, 4))
                alpha = int(220 * brightness); h_radius = 12
                draw.ellipse((dot['x']-h_radius, dot['y']-h_radius, dot['x']+h_radius, dot['y']+h_radius), fill=(r,g,b,alpha))
        playhead_x = 140 + (1000 * (current_time / duration_sec)); y_top = 100; y_bottom = 100 + (len(specs_data) - 1) * 120
        draw.line((playhead_x, y_top - 10, playhead_x, y_bottom + 10), fill=(255, 255, 255, 150), width=3)
        frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png"); frame_img.convert("RGB").save(frame_path)
        
    print(f"{total_frames}枚のフレームを生成しました。")
    ffmpeg_command = ["ffmpeg","-y","-framerate",str(fps),"-i",os.path.join(temp_dir,"frame_%04d.png"),"-i",sound_path,"-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-preset","veryfast","-crf","28",out_path]
    print(f"FFmpegコマンドを実行: {' '.join(ffmpeg_command)}")
    subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
    print(f"動画を生成しました: {out_path}"); shutil.rmtree(temp_dir); print("一時ファイルを削除しました。")
def make_base_image(spec, judge_window, specs_data, bpm):
    n=len(specs_data); TOP_MARGIN=100; LEFT=140; SPACING=120; DOT_R=9; LEFT_LABEL_SIZE=48; TOP_TITLE_SIZE=56; BOTTOM_MARGIN=30; width=1200; line_len=1000
    height = TOP_MARGIN + n * SPACING + BOTTOM_MARGIN
    img = Image.new("RGBA", (width, height), (0,0,0,255)); draw = ImageDraw.Draw(img)
    font_label=load_font(LEFT_LABEL_SIZE); font_title=load_font(TOP_TITLE_SIZE)
    title = spec.replace(":", " : "); tw, th = text_size(draw, title, font_title)
    draw.text(((width-tw)/2, 18), title, fill="white", font=font_title)
    left=LEFT; right=left+line_len; bar_line_color="#555555"; bar_line_width=4
    y_top = TOP_MARGIN; y_bottom = TOP_MARGIN + (len(specs_data) - 1) * 120 if n > 0 else TOP_MARGIN
    for x_pos in [left, left + line_len / 2, right]: draw.line((x_pos, y_top, x_pos, y_bottom), fill=bar_line_color, width=bar_line_width)
    for i, s in enumerate(specs_data):
        k=s['k']; label=s['label']; y=TOP_MARGIN + i * SPACING; dark_green="#009A00"; bright_green="#90FF90"
        draw.line((left, y, right, y), fill=dark_green, width=4); color=s['color']; stroke_color=darken_color(color)
        dot_centers=[]
        if s['is_off_beat']:
            for j in range(k): dot_centers.append(left + (line_len * (j + 0.5)) / k)
        else:
            for j in range(k+1): dot_centers.append(left + (line_len * j) / k)
        if judge_window and dot_centers:
            JUDGE_MS=166.6; BAR_MS=3000.0; judge_width_half_px=line_len*(JUDGE_MS/BAR_MS)
            theoretical_judges=[{'center':x,'left':x-judge_width_half_px,'right':x+judge_width_half_px} for x in dot_centers]
            actual_judges=[j.copy() for j in theoretical_judges]
            for j in range(len(theoretical_judges)-1):
                if theoretical_judges[j]['right']>theoretical_judges[j+1]['left']:
                    midpoint=(theoretical_judges[j]['center']+theoretical_judges[j+1]['center'])/2
                    actual_judges[j]['right']=midpoint; actual_judges[j+1]['left']=midpoint
            if actual_judges:
                actual_judges[0]['left']=max(left,actual_judges[0]['left']); actual_judges[-1]['right']=min(right,actual_judges[-1]['right'])
            separator_height=8
            for segment in actual_judges:
                draw.line((segment['left'],y,segment['right'],y),fill=bright_green,width=2)
                draw.line((segment['left'],y-separator_height/2,segment['left'],y+separator_height/2),fill="white",width=2)
                draw.line((segment['right'],y-separator_height/2,segment['right'],y+separator_height/2),fill="white",width=2)
        tick_height=8
        for x in dot_centers:
            draw.line((x,y-tick_height/2,x,y+tick_height/2),fill="black",width=2)
            draw.ellipse((x-DOT_R,y-DOT_R,x+DOT_R,y+DOT_R),fill=color,outline=stroke_color,width=3)
        lw,lh=text_size(draw,label,font_label); draw.text((30,y-lh/2),label,fill=color,font=font_label,stroke_width=3,stroke_fill=stroke_color)
    return img

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("spec")
    p.add_argument("out", nargs='?', default="polyrhythm.png")
    p.add_argument("--video", action="store_true")
    p.add_argument("--bpm", type=int, default=120)
    p.add_argument("--judge-window", action="store_true")
    p.add_argument("--audio-only", action="store_true")
    args = p.parse_args()

    if args.audio_only:
        out_path = os.path.splitext(args.out)[0] + ".mp3"
        make_audio_only(args.spec, out_path, args.bpm)
    elif args.video:
        out_path = os.path.splitext(args.out)[0] + ".mp4"
        make_video(args.spec, out_path, args.bpm, args.judge_window)
    else:
        specs = parse_spec(args.spec)
        img = make_base_image(args.spec, args.judge_window, specs, args.bpm)
        img.convert("RGB").save(args.out)
        print(f"静止画を保存しました: {args.out}")
PY
from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
from src import DataLoader, TxtAgent, ImgAgent, VidAgent
from src import ref_viz
from src.retry import RETRY_BACKOFF, RETRY_DELAY, TASK_ATTEMPTS
from src.traits import format_trait
from dotenv import load_dotenv

import threading
import time
import traceback
import uuid

load_dotenv(override=True)

app = Flask(__name__)

# Initialize data loader
data_loader = DataLoader()

# Load metadata
neopir_meta = data_loader.load_meta("NEO-PI-R")
neopir = data_loader.load("NEO-PI-R", "zh")
sjts_data = data_loader.load("PSJT-Mussel", "zh")

# Output directory
outdir = Path("./outputs")
outdir.mkdir(exist_ok=True, parents=True)


# ---------------------------------------------------------------------------
# Background task manager
#
# Generation can take minutes. Running it inside the request means the work is
# tied to the page: navigating away aborts the fetch and the result is lost.
# Instead every generation runs in a daemon thread and the client polls for it,
# so switching pages (or reloading) never kills a running job.
# ---------------------------------------------------------------------------

_tasks = {}
_tasks_lock = threading.Lock()
MAX_TASKS = 50


def _public_task(task):
    """Serializable view of a task (drops the internal callable/params)."""
    return {
        'task_id': task['task_id'],
        'kind': task['kind'],
        'label': task['label'],
        'status': task['status'],
        'result': task['result'],
        'error': task['error'],
        'created_at': task['created_at'],
        'finished_at': task['finished_at'],
        'attempt': task.get('attempt', 1),
        'attempts': task.get('attempts', 1),
    }


def _prune_tasks():
    """Drop the oldest finished tasks once we exceed MAX_TASKS (caller holds lock)."""
    finished = sorted(
        (t for t in _tasks.values() if t['status'] != 'running'),
        key=lambda t: t['created_at'],
    )
    while len(_tasks) > MAX_TASKS and finished:
        del _tasks[finished.pop(0)['task_id']]


def _run_task(task_id, fn, attempts=TASK_ATTEMPTS):
    """跑一个生成任务；失败自动重来，全部尝试都失败才算错误。

    生成链路上每一步都依赖 LLM，偶发的格式/网关问题重跑一次基本就能过，
    没必要让用户自己点第二次。
    """
    attempts = max(1, int(attempts))
    wait = RETRY_DELAY
    for attempt in range(1, attempts + 1):
        try:
            result = fn()
            with _tasks_lock:
                _tasks[task_id].update(
                    status='done', result=result, finished_at=time.time())
            return
        except Exception as e:
            traceback.print_exc()
            if attempt == attempts:
                with _tasks_lock:
                    _tasks[task_id].update(
                        status='error', error=str(e), finished_at=time.time())
                return
            with _tasks_lock:
                label = _tasks.get(task_id, {}).get('label', task_id)
                if task_id in _tasks:
                    _tasks[task_id]['attempt'] = attempt + 1
            print(f"[task] {label} 第 {attempt}/{attempts} 次失败：{e}；{wait:.0f}s 后重试")
            time.sleep(wait)
            wait *= RETRY_BACKOFF


def submit_task(kind, label, fn):
    """Start `fn` in the background and return its task id."""
    task_id = uuid.uuid4().hex
    with _tasks_lock:
        _tasks[task_id] = {
            'task_id': task_id,
            'kind': kind,
            'label': label,
            'status': 'running',
            'result': None,
            'error': None,
            'created_at': time.time(),
            'finished_at': None,
            'attempt': 1,
            'attempts': TASK_ATTEMPTS,
        }
        _prune_tasks()

    threading.Thread(target=_run_task, args=(task_id, fn), daemon=True).start()
    return task_id


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task(task_id):
    """Poll a single generation task."""
    with _tasks_lock:
        task = _tasks.get(task_id)
        if task is None:
            return jsonify({'error': 'Task not found', 'status': 'missing'}), 404
        return jsonify(_public_task(task))


@app.route('/api/task/<task_id>', methods=['DELETE'])
def forget_task(task_id):
    """Forget a finished task so it stops showing up in the running list."""
    with _tasks_lock:
        task = _tasks.get(task_id)
        if task is None:
            return jsonify({'error': 'Task not found'}), 404
        if task['status'] == 'running':
            return jsonify({'error': 'Task is still running'}), 409
        del _tasks[task_id]
    return jsonify({'success': True})


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """List known tasks, newest first. `?status=running` filters to active ones."""
    wanted = request.args.get('status')
    with _tasks_lock:
        tasks = [_public_task(t) for t in _tasks.values()
                 if wanted is None or t['status'] == wanted]
    tasks.sort(key=lambda t: t['created_at'], reverse=True)
    # The list view only needs the headline, not the payload.
    for t in tasks:
        t.pop('result', None)
    return jsonify({'tasks': tasks})


@app.route('/outputs/<path:filename>')
def serve_output_file(filename):
    """Serve files from the outputs directory"""
    return send_from_directory(outdir, filename)


@app.route('/')
def index():
    """Main page with trait and item selector"""
    return render_template('index.html', traits=neopir_meta)


@app.route('/api/traits', methods=['GET'])
def get_traits():
    """API endpoint to get all traits"""
    return jsonify(neopir_meta)


@app.route('/api/items/<trait_id>', methods=['GET'])
def get_items(trait_id):
    """API endpoint to get items for a specific trait"""
    if trait_id not in neopir:
        return jsonify({'error': 'Trait not found'}), 404

    items = neopir[trait_id]['items']
    return jsonify(items)


@app.route('/api/situations/<trait_id>', methods=['GET'])
def get_situations(trait_id):
    """API endpoint to get SJT situations for a specific trait"""
    if trait_id not in sjts_data:
        return jsonify({'error': 'No situations found for this trait', 'available': False}), 404

    situations = sjts_data[trait_id]
    return jsonify({
        'available': True,
        'situations': situations
    })


@app.route('/text-sjt')
def text_sjt():
    """Text SJT generation page"""
    return render_template('text_sjt.html', traits=neopir_meta)


@app.route('/image-sjt')
def image_sjt():
    """Image SJT generation page"""
    # Filter traits that have available situations
    available_traits = {
        trait_id: trait_info
        for trait_id, trait_info in neopir_meta.items()
        if trait_id in sjts_data
    }
    return render_template('image_sjt.html', traits=available_traits)


@app.route('/video-sjt')
def video_sjt():
    """Video SJT generation page"""
    # Filter traits that have available situations
    available_traits = {
        trait_id: trait_info
        for trait_id, trait_info in neopir_meta.items()
        if trait_id in sjts_data
    }
    return render_template('video_sjt.html', traits=available_traits)


@app.route('/quiz')
def quiz():
    """Quiz display page for generated content"""
    import json
    generated_dir = Path("./generated")
    
    sjt_data = {}
    for json_file in ['sjt_txt.json', 'sjt_img.json', 'sjt_vid.json']:
        file_path = generated_dir / json_file
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                sjt_type = json_file.replace('sjt_', '').replace('.json', '')
                sjt_data[sjt_type] = json.load(f)
    
    return render_template('quiz.html', sjt_data=sjt_data)


@app.route('/generated/<path:filename>')
def serve_generated_file(filename):
    """Serve files from the generated directory"""
    return send_from_directory('./generated', filename)


@app.route('/api/generate/text', methods=['POST'])
def generate_text():
    """Kick off text SJT generation in the background"""
    try:
        data = request.json
        trait_id = data.get('trait_id')
        item_id = data.get('item_id')
        situation_theme = data.get('situation_theme', '大学生活')
        target_population = data.get('target_population', '中国大学生')
        n_items = data.get('n_items', 1)

        if not trait_id or not item_id:
            return jsonify({'error': 'Missing trait_id or item_id'}), 400

        # Get trait info
        trait_meta = neopir_meta[trait_id]
        item_text = neopir[trait_id]['items'][item_id]['item']

        def job():
            # Initialize agent
            txt_agent = TxtAgent(
                situation_theme=situation_theme,
                target_population=target_population,
            )

            # Generate SJT
            result = txt_agent.run(
                trait_name=trait_meta['facet_name'],
                trait_description=trait_meta['description'],
                low_score=trait_meta['low_score'],
                high_score=trait_meta['high_score'],
                item=item_text,
                n_item=n_items,
                outdir=outdir,
                out_basename=f"SJT_{trait_id}_{item_id}"
            )

            # Handle different result structures
            if isinstance(result, dict):
                result_data = result.get('items', result)
            else:
                result_data = result

            # Ensure result_data is a list
            if not isinstance(result_data, list):
                result_data = [result_data] if result_data else []

            return {
                'success': True,
                'result': result_data,
                'output_file': f"SJT_{trait_id}_{item_id}.json"
            }

        task_id = submit_task('text', f"文字题目 {trait_id}-{item_id}", job)
        return jsonify({'success': True, 'task_id': task_id, 'status': 'running'}), 202

    except KeyError as e:
        return jsonify({'error': f'Invalid trait_id or item_id: {str(e)}'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate/image', methods=['POST'])
def generate_image():
    """Kick off image SJT generation in the background"""
    try:
        data = request.json
        trait_id = data.get('trait_id')
        item_id = data.get('item_id')
        ref_character = data.get('ref_character', 'male')
        run_bubble = data.get('run_bubble', True)

        if not trait_id or not item_id:
            return jsonify({'error': 'Missing trait_id or item_id'}), 400

        # Get trait info
        trait_meta = neopir_meta[trait_id]

        # Get SJT situation data
        if trait_id not in sjts_data or item_id not in sjts_data[trait_id]:
            return jsonify({'error': 'SJT situation not found for this trait/item'}), 404

        basename = f"SJT_{trait_id}_{item_id}"

        def job():
            # Initialize agent
            img_agent = ImgAgent(
                situ=sjts_data[trait_id][item_id],
                # 提示词以大五维度为框架，只给面名称（如「价值观」）时模型会拒答，
                # 所以补上所属维度。
                trait=format_trait(trait_id, trait_meta),
                ref_viz=ref_viz.get(ref_character, ref_viz['male'])
            )

            # Generate image SJT
            result = img_agent.run(
                run_bubble=run_bubble,
                outdir=str(outdir),
                out_basename=basename
            )

            # Extract image files from result
            image_files = []

            # Get the situation image from result
            if result and 'situation' in result:
                situation_path = Path(result['situation'])
                if situation_path.exists():
                    # Extract just the filename relative to outdir
                    image_files.append(situation_path.name)

            return {
                'success': True,
                'result': result,
                'output_file': basename,
                'image_files': image_files,  # List of generated image files
                'has_images': len(image_files) > 0
            }

        task_id = submit_task('image', f"图片题目 {trait_id}-{item_id}", job)
        return jsonify({'success': True, 'task_id': task_id, 'status': 'running'}), 202

    except KeyError as e:
        return jsonify({'error': f'Invalid trait_id or item_id: {str(e)}'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate/video', methods=['POST'])
def generate_video():
    """Kick off video SJT generation in the background"""
    try:
        data = request.json
        trait_id = data.get('trait_id')
        item_id = data.get('item_id')

        if not trait_id or not item_id:
            return jsonify({'error': 'Missing trait_id or item_id'}), 400

        # Get trait info
        trait_meta = neopir_meta[trait_id]

        # Get SJT situation data
        if trait_id not in sjts_data or item_id not in sjts_data[trait_id]:
            return jsonify({'error': 'SJT situation not found for this trait/item'}), 404

        basename = f"SJT_{trait_id}_{item_id}"

        def job():
            # Initialize agent
            vid_agent = VidAgent(
                situ=sjts_data[trait_id][item_id],
                # 同图像流程：反思智能体按大五维度对齐构念，需要维度信息
                trait=format_trait(trait_id, trait_meta),
            )

            # Generate video SJT
            result = vid_agent.run(
                outdir=outdir,
                out_basename=basename
            )

            # Find generated video files
            video_files = []
            for ext in ['.mp4', '.avi', '.mov', '.webm']:
                vid_path = outdir / f"{basename}{ext}"
                if vid_path.exists():
                    video_files.append(f"{basename}{ext}")

            # Also check for numbered files
            for file in outdir.glob(f"{basename}_*.mp4"):
                video_files.append(file.name)
            for file in outdir.glob(f"{basename}_*.avi"):
                video_files.append(file.name)
            for file in outdir.glob(f"{basename}_*.mov"):
                video_files.append(file.name)

            return {
                'success': True,
                'result': result,
                'output_file': basename,
                'video_files': video_files,  # List of generated video files
                'has_videos': len(video_files) > 0
            }

        task_id = submit_task('video', f"视频题目 {trait_id}-{item_id}", job)
        return jsonify({'success': True, 'task_id': task_id, 'status': 'running'}), 202

    except KeyError as e:
        return jsonify({'error': f'Invalid trait_id or item_id: {str(e)}'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4399, threaded=True)

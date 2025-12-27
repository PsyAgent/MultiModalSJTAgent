from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
from src import DataLoader, TxtAgent, ImgAgent, VidAgent
from src import ref_viz
from dotenv import load_dotenv

load_dotenv()

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
    """Generate text SJT"""
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

        # Log the result structure for debugging
        print(f"Result type: {type(result)}")
        print(f"Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        # Handle different result structures
        if isinstance(result, dict):
            if 'items' in result:
                result_data = result['items']
            else:
                # If no 'items' key, return the whole result
                result_data = result
        else:
            result_data = result

        # Ensure result_data is a list
        if not isinstance(result_data, list):
            result_data = [result_data] if result_data else []

        return jsonify({
            'success': True,
            'result': result_data,
            'output_file': f"SJT_{trait_id}_{item_id}.json"
        })

    except KeyError as e:
        return jsonify({'error': f'Invalid trait_id or item_id: {str(e)}'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate/image', methods=['POST'])
def generate_image():
    """Generate image SJT"""
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

        # Initialize agent
        img_agent = ImgAgent(
            situ=sjts_data[trait_id][item_id],
            trait=trait_meta['facet_name'],
            ref_viz=ref_viz.get(ref_character, ref_viz['male'])
        )

        # Generate image SJT
        basename = f"SJT_{trait_id}_{item_id}"
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

        return jsonify({
            'success': True,
            'result': result,
            'output_file': basename,
            'image_files': image_files,  # List of generated image files
            'has_images': len(image_files) > 0
        })

    except KeyError as e:
        return jsonify({'error': f'Invalid trait_id or item_id: {str(e)}'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate/video', methods=['POST'])
def generate_video():
    """Generate video SJT"""
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

        # Initialize agent
        vid_agent = VidAgent(
            situ=sjts_data[trait_id][item_id],
            trait=trait_meta['facet_name'],
        )

        # Generate video SJT
        basename = f"SJT_{trait_id}_{item_id}"
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

        return jsonify({
            'success': True,
            'result': result,
            'output_file': basename,
            'video_files': video_files,  # List of generated video files
            'has_videos': len(video_files) > 0
        })

    except KeyError as e:
        return jsonify({'error': f'Invalid trait_id or item_id: {str(e)}'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4399)

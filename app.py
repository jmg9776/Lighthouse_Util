from flask import Flask, request, jsonify, send_from_directory, render_template_string, redirect, url_for
import subprocess
import os
from datetime import datetime
from threading import Thread
import secrets

app = Flask(__name__)

RESULTS_DIR = 'lighthouse_results'
os.makedirs(RESULTS_DIR, exist_ok=True)


def generate_random_secret_key():
    return secrets.token_hex(24)


secret_key = generate_random_secret_key()
print(f"Generated Secret Key: {secret_key}")


def get_filename_from_url(url, version='desktop'):
    clean_url = url.replace("http://", "").replace("https://", "")
    filename = clean_url.replace("/", "_").replace("?", "_")
    return f"{filename}_{version}.html"


def get_timestamp():
    return datetime.now().strftime('%Y%m%d%H%M%S')


def format_request_id_for_display(request_id):
    dt = datetime.strptime(request_id, '%Y%m%d%H%M%S')
    return dt.strftime('%m월 %d일 %H시 %M분 결과')


def analyze_with_lighthouse(request_id, urlList):
    request_dir = os.path.join(RESULTS_DIR, request_id)
    os.makedirs(request_dir, exist_ok=True)

    for url in urlList:
        for version in ['desktop', 'mobile']:
            filename = get_filename_from_url(url, version)
            filepath = os.path.join(request_dir, filename)
            config_path = f"{version}.json"  # Assuming desktop.json and mobile.json are present
            command = f"lighthouse {url} --output=html --output-path={filepath} --quiet --no-enable-error-reporting --chrome-flags=\"--headless --window-size=1920,1080\" --config-path={config_path} --locale=ko"
            subprocess.run(command, shell=True)
    print("Analysis complete")


@app.route('/analyze', methods=['POST'])
def analyze_urls():
    data = request.json
    request_secret_key = data.get('secret_key')
    urls = data.get('urls')

    if request_secret_key != secret_key:
        return jsonify({"error": "Invalid secret key"}), 403

    if not urls:
        return jsonify({"error": "URLs not provided"}), 400

    request_id = get_timestamp()
    thread = Thread(target=analyze_with_lighthouse, args=(request_id, urls))
    thread.start()

    return jsonify({"message": "Analysis started", "requestId": request_id})


@app.route('/delete/<request_id>', methods=['GET'])
def delete_report(request_id):
    request_dir = os.path.join(RESULTS_DIR, request_id)
    try:
        for filename in os.listdir(request_dir):
            file_path = os.path.join(request_dir, filename)
            os.remove(file_path)
        os.rmdir(request_dir)
        return redirect(url_for('list_requests'))
    except FileNotFoundError:
        return jsonify({"error": "Request ID or file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/', methods=['GET'])
def list_requests():
    request_dirs = sorted(os.listdir(RESULTS_DIR), reverse=True)
    links = [{'href': f'/{request_dir}', 'text': format_request_id_for_display(request_dir)} for request_dir in
             request_dirs]

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lighthouse 분석 요청 목록</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container d-flex justify-content-center align-items-center" style="height: 100vh;">
            <div class="card" style="min-width: 500px;">
                <div class="card-body">
                    <h5 class="card-title">Lighthouse 분석 요청 목록</h5>
                    <div class="list-group" style="max-height:500px; overflow-y:scroll">
                        {% for link in links %}
                            <div class="d-flex justify-content-between align-items-center list-group-item">
                                <a href="/requests/{{ link.href }}" class="flex-grow-1 mr-3">{{ link.text }}</a>
                                <!-- 모든 파일 삭제 버튼 추가 -->
                                <a href="/delete/{{ link.href }}" class="btn btn-danger btn-sm" onclick="return confirm('해당 분석 결과를 모두 삭제하시겠습니까?');">삭제</a>
                            </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """, links=links)


@app.route('/requests/<request_id>', methods=['GET'])
def list_reports_in_request(request_id):
    files = os.listdir(os.path.join(RESULTS_DIR, request_id))
    links = [{'href': f'/report/{request_id}/{file}', 'text': file} for file in files]

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lighthouse 분석 결과 목록</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container d-flex justify-content-center align-items-center" style="height: 100vh;">
            <div class="card"  style="min-width:500px">
                <div class="card-body">
                    <h5 class="card-title">Lighthouse 분석 결과 목록</h5>
                    <div class="list-group" style="max-height:500px; overflow-y:scroll">
                        {% for link in links %}
                            <a href="{{ link.href }}" class="list-group-item list-group-item-action">{{ link.text }}</a>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """, links=links)


@app.route('/report/<request_id>/<filename>', methods=['GET'])
def view_report(request_id, filename):
    return send_from_directory(os.path.join(RESULTS_DIR, request_id), filename)


if __name__ == '__main__':
    app.run(debug=True)

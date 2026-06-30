from flask import Flask, render_template, request, jsonify
import docker

app = Flask(__name__)
client = docker.from_env()

# ====================== API 接口 ======================

@app.route('/api/containers')
def api_containers():
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '').strip().lower()
    page = int(request.args.get('page', 1))
    per_page = 15

    containers = []
    for c in client.containers.list(all=True):
        containers.append({
            'id': c.short_id,
            'name': c.name,
            'image': c.image.tags[0] if c.image.tags else c.image.id[:12],
            'status': c.status,
            'ports': c.ports,
            'created': c.attrs['Created'][:19].replace('T', ' ')
        })

    # 搜索（按名称）
    if search_query:
        containers = [c for c in containers if search_query in c['name'].lower()]

    # 状态筛选
    if status_filter != 'all':
        containers = [c for c in containers if c['status'] == status_filter]

    # 分页
    total = len(containers)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages or 1))
    start = (page - 1) * per_page
    containers = containers[start:start + per_page]

    return jsonify({
        'containers': containers,
        'page': page,
        'total_pages': total_pages,
        'total': total,
        'status': status_filter
    })

@app.route('/api/container/<container_id>')
def api_container_detail(container_id):
    try:
        c = client.containers.get(container_id)
        attrs = c.attrs
        return jsonify({
            'success': True,
            'id': c.id[:12],
            'name': c.name,
            'image': c.image.tags[0] if c.image.tags else c.image.id[:12],
            'status': c.status,
            'created': attrs['Created'][:19].replace('T', ' '),
            'ports': str(c.ports),
            'command': ' '.join(attrs['Config'].get('Cmd', [])),
            'env': '\n'.join(attrs['Config'].get('Env', [])),
            'volumes': str([m['Destination'] for m in attrs.get('Mounts', [])])
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/<action>/<container_id>', methods=['POST'])
def api_action(action, container_id):
    try:
        container = client.containers.get(container_id)
        
        if action == 'start':
            container.start()
            msg = '容器已启动'
        elif action == 'stop':
            container.stop(timeout=10)
            msg = '容器已停止'
        elif action == 'restart':
            container.restart(timeout=10)
            msg = '容器已重启'
        elif action == 'remove':
            if container.status == 'running':
                container.stop(timeout=5)
            container.remove(force=True)
            msg = '容器已删除'
        elif action == 'update':
            image_name = container.image.tags[0] if container.image.tags else container.image.id
            client.images.pull(image_name)
            if container.status == 'running':
                container.stop(timeout=10)
            container.remove(force=True)
            client.containers.run(image=image_name, name=container.name, detach=True)
            msg = '容器更新成功'
        else:
            return jsonify({'success': False, 'message': '未知操作'}), 400

        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/pull', methods=['POST'])
def api_pull():
    try:
        data = request.json
        image = data.get('image')
        if not image:
            return jsonify({'success': False, 'message': '镜像名称不能为空'}), 400
        client.images.pull(image)
        return jsonify({'success': True, 'message': f'镜像 {image} 拉取成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# ====================== 前端页面 ======================
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=False)
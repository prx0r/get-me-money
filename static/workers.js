// Moltwork Workshop — 3D Worker Characters
// Three.js visualization of workers in the workshop

class MoltworkWorkshop {
    constructor(container) {
        this.container = container;
        this.workers = [];
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.init();
    }

    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a0f);

        // Camera
        this.camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.camera.position.set(0, 5, 12);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.container.appendChild(this.renderer.domElement);

        // Lights
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);
        const pointLight = new THREE.PointLight(0xffffff, 1, 100);
        pointLight.position.set(10, 10, 10);
        this.scene.add(pointLight);

        // Workshop floor
        const floorGeo = new THREE.PlaneGeometry(20, 20);
        const floorMat = new THREE.MeshStandardMaterial({ color: 0x1a1a2e, metalness: 0.3, roughness: 0.8 });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -1;
        this.scene.add(floor);

        // Grid
        const grid = new THREE.GridHelper(20, 20, 0x2a2a4a, 0x1a1a3a);
        grid.position.y = -0.99;
        this.scene.add(grid);

        // Add workers
        this.addWorkers();

        // Animate
        this.animate();

        // Handle resize
        window.addEventListener('resize', () => this.onResize());
    }

    addWorkers() {
        const workerData = [
            { name: 'Scout', color: 0x4a9eff, emoji: '🔍', pos: [-3, 0, 0], skills: ['research', 'verification'] },
            { name: 'Forge', color: 0xff6b4a, emoji: '⚒️', pos: [-1, 0, 0], skills: ['coding', 'review'] },
            { name: 'Oracle', color: 0x4aff8b, emoji: '🔮', pos: [1, 0, 0], skills: ['analysis', 'extraction'] },
            { name: 'Relay', color: 0xffb84a, emoji: '⚡', pos: [3, 0, 0], skills: ['api', 'automation'] },
        ];

        workerData.forEach((wd, i) => {
            const group = new THREE.Group();
            group.position.set(...wd.pos);

            // Body (capsule)
            const bodyGeo = new THREE.CapsuleGeometry(0.4, 1, 8, 16);
            const bodyMat = new THREE.MeshStandardMaterial({
                color: wd.color,
                metalness: 0.4,
                roughness: 0.3,
                emissive: wd.color,
                emissiveIntensity: 0.2
            });
            const body = new THREE.Mesh(bodyGeo, bodyMat);
            body.position.y = 0.5;
            group.add(body);

            // Head
            const headGeo = new THREE.SphereGeometry(0.3, 16, 16);
            const headMat = new THREE.MeshStandardMaterial({
                color: wd.color,
                metalness: 0.5,
                roughness: 0.2,
                emissive: wd.color,
                emissiveIntensity: 0.3
            });
            const head = new THREE.Mesh(headGeo, headMat);
            head.position.y = 1.5;
            group.add(head);

            // Eyes (glowing)
            const eyeGeo = new THREE.SphereGeometry(0.06, 8, 8);
            const eyeMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.8 });
            const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
            leftEye.position.set(-0.1, 1.55, 0.25);
            group.add(leftEye);
            const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
            rightEye.position.set(0.1, 1.55, 0.25);
            group.add(rightEye);

            // Workbench
            const benchGeo = new THREE.BoxGeometry(1.2, 0.1, 0.8);
            const benchMat = new THREE.MeshStandardMaterial({ color: 0x3a3a5a, metalness: 0.2, roughness: 0.7 });
            const bench = new THREE.Mesh(benchGeo, benchMat);
            bench.position.set(0, 0, 0.8);
            group.add(bench);

            // Name label (sprite)
            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 64;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = 'transparent';
            ctx.fillRect(0, 0, 256, 64);
            ctx.fillStyle = '#' + wd.color.toString(16).padStart(6, '0');
            ctx.font = 'bold 32px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(wd.name, 128, 40);
            const texture = new THREE.CanvasTexture(canvas);
            const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
            const sprite = new THREE.Sprite(spriteMat);
            sprite.position.set(0, 2.2, 0);
            sprite.scale.set(2, 0.5, 1);
            group.add(sprite);

            // Store reference
            group.userData = { name: wd.name, color: wd.color, skills: wd.skills, baseY: 0 };
            this.workers.push(group);
            this.scene.add(group);
        });
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const time = Date.now() * 0.001;

        this.workers.forEach((worker, i) => {
            // Floating animation
            worker.position.y = Math.sin(time + i * 0.5) * 0.1;

            // Gentle rotation
            worker.rotation.y = Math.sin(time * 0.3 + i) * 0.1;
        });

        // Camera orbit
        this.camera.position.x = Math.sin(time * 0.1) * 2;
        this.camera.lookAt(0, 0.5, 0);

        this.renderer.render(this.scene, this.camera);
    }

    onResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    // Highlight a worker (when it's active)
    highlight(name) {
        this.workers.forEach(w => {
            if (w.userData.name === name) {
                w.children[0].material.emissiveIntensity = 0.8;
                w.children[1].material.emissiveIntensity = 0.9;
            } else {
                w.children[0].material.emissiveIntensity = 0.2;
                w.children[1].material.emissiveIntensity = 0.3;
            }
        });
    }
}

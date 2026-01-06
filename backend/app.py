from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
import torchvision.transforms as transforms
from PIL import Image
import io
import base64
import numpy as np
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

# Modelleri yükle
print("Loading models...")

# ResNet modeli (kıyafet sınıflandırma için)
resnet_model = None
try:
    resnet_model = torch.load('models/resnet_model.pth', map_location=torch.device('cpu'))
    resnet_model.eval()
    print("ResNet model loaded successfully")
except Exception as e:
    print(f"ResNet model loading error: {e}")

# YOLO modeli (kıyafet tespiti için)
yolo_model = None
try:
    yolo_model = YOLO('models/yolo_model.pt')
    print("YOLO model loaded successfully")
except Exception as e:
    print(f"YOLO model loading error: {e}")

# Image preprocessing for ResNet
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Kıyafet kategorileri (modelinize göre güncelleyin)
CLOTHING_CATEGORIES = [
    'T-shirt', 'Gömlek', 'Kazak', 'Ceket', 'Pantolon', 
    'Etek', 'Elbise', 'Ayakkabı', 'Çanta', 'Aksesuar'
]

@app.route('/health', methods=['GET'])
def health_check():
    """API sağlık kontrolü"""
    return jsonify({
        'status': 'healthy',
        'resnet_loaded': resnet_model is not None,
        'yolo_loaded': yolo_model is not None
    })

@app.route('/api/classify', methods=['POST'])
def classify_clothing():
    """ResNet ile kıyafet sınıflandırma"""
    try:
        if resnet_model is None:
            return jsonify({'error': 'ResNet model not loaded'}), 500
        
        # Resmi al
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        image = Image.open(image_file.stream).convert('RGB')
        
        # Preprocessing
        input_tensor = transform(image).unsqueeze(0)
        
        # Tahmin yap
        with torch.no_grad():
            outputs = resnet_model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
        
        predicted_class = predicted.item()
        confidence_score = confidence.item()
        
        # Kategori adını al
        category = CLOTHING_CATEGORIES[predicted_class] if predicted_class < len(CLOTHING_CATEGORIES) else f"Category {predicted_class}"
        
        return jsonify({
            'success': True,
            'category': category,
            'confidence': float(confidence_score),
            'class_id': int(predicted_class)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect', methods=['POST'])
def detect_clothing():
    """YOLO ile kıyafet tespiti"""
    try:
        if yolo_model is None:
            return jsonify({'error': 'YOLO model not loaded'}), 500
        
        # Resmi al
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        image = Image.open(image_file.stream).convert('RGB')
        
        # YOLO ile tespit yap
        results = yolo_model(image)
        
        # Sonuçları parse et
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                detection = {
                    'bbox': box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
                    'confidence': float(box.conf[0]),
                    'class_id': int(box.cls[0]),
                    'class_name': result.names[int(box.cls[0])]
                }
                detections.append(detection)
        
        return jsonify({
            'success': True,
            'detections': detections,
            'count': len(detections)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_outfit():
    """Kombin analizi - hem tespit hem sınıflandırma"""
    try:
        if yolo_model is None or resnet_model is None:
            return jsonify({'error': 'Models not loaded'}), 500
        
        # Resmi al
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        image = Image.open(image_file.stream).convert('RGB')
        
        # 1. YOLO ile kıyafetleri tespit et
        yolo_results = yolo_model(image)
        
        # 2. Her tespit edilen kıyafeti ResNet ile sınıflandır
        analyzed_items = []
        for result in yolo_results:
            boxes = result.boxes
            for box in boxes:
                # Crop the detected region
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cropped_image = image.crop((x1, y1, x2, y2))
                
                # ResNet ile sınıflandır
                input_tensor = transform(cropped_image).unsqueeze(0)
                with torch.no_grad():
                    outputs = resnet_model(input_tensor)
                    probabilities = torch.nn.functional.softmax(outputs, dim=1)
                    confidence, predicted = torch.max(probabilities, 1)
                
                predicted_class = predicted.item()
                category = CLOTHING_CATEGORIES[predicted_class] if predicted_class < len(CLOTHING_CATEGORIES) else f"Category {predicted_class}"
                
                analyzed_items.append({
                    'bbox': [x1, y1, x2, y2],
                    'yolo_class': result.names[int(box.cls[0])],
                    'yolo_confidence': float(box.conf[0]),
                    'resnet_category': category,
                    'resnet_confidence': float(confidence.item())
                })
        
        return jsonify({
            'success': True,
            'items': analyzed_items,
            'count': len(analyzed_items)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Smart Wardrobe AI Backend...")
    print("Make sure your models are in the 'models/' directory:")
    print("  - models/resnet_model.pth")
    print("  - models/yolo_model.pt")
    app.run(host='0.0.0.0', port=5000, debug=True)

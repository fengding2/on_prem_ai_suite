
import json
import cv2

# file_path = './b827ebc347bd_1569401833.jpg'
# plot_json = """{"device_id":"b827ebc347bd","file_name":"b827ebc347bd_1569401833.jpg","boxes":[{"activities":["standing","walking","talking","sitting","relaxing"],"loc":[462,0,49,126]},{"activities":["working","sitting","talking"],"loc":[362,110,113,190]},{"activities":["sitting","working","talking","relaxing"],"loc":[495,55,64,120]},{"activities":["working","sitting","talking"],"loc":[335,69,130,167]},{"activities":[],"loc":[376,156,162,300]}]}"""

file_path = './b827ebf39c8c_1569446912.jpg'
plot_json = '{"device_id":"b827ebf39c8c","file_name":"b827ebf39c8c_1569446912.jpg","boxes":[{"activities":["sitting","talking"],"loc":[92,59,100,189]}]}'

def draw_rectangle(file_path, boxes):
    img = cv2.imread(file_path, cv2.IMREAD_COLOR)
    for box in boxes:
        text = box['activities']
        [x, y, w, h] = box['loc']
        # Get the unique color for this class
        color = [0,255,0]
        # Draw the bounding box rectangle and label on the image
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        if len(text) > 0:
            cv2.putText(img, text[0], (x+5, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return img

def save_result_img(img):
    output_path = './out.jpg'
    cv2.imwrite(output_path,img)


if __name__ == "__main__":
    result_json = json.loads(plot_json)
    device_id = result_json['device_id']
    file_name = result_json['file_name']
    boxes = result_json['boxes']
    img = draw_rectangle(file_path, boxes)
    save_result_img(img)

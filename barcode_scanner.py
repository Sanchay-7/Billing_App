import cv2
from pyzbar.pyzbar import decode

def scan_and_add_loop(add_callback):
    cap = cv2.VideoCapture(0)
    last_code = ""

    print("📷 Auto-scanning... Press Q to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        barcodes = decode(frame)
        for barcode in barcodes:
            code = barcode.data.decode("utf-8")

            if code != last_code:
                print(f"✅ Scanned: {code}")
                last_code = code
                add_callback(code)

        cv2.imshow("Auto Scanner (Press Q to stop)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


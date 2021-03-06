""" 
Code author : DoranLyong 

Reference : 
* https://docs.python.org/3.7/library/socketserver.html
* https://webnautes.tistory.com/1382
* https://github.com/IntelRealSense/librealsense/tree/master/wrappers/python/examples
* http://blog.cogitomethods.com/visual-analytics-using-opencv-and-realsense-camera/
"""
import socketserver
import socket
from queue import Queue
from _thread import *

import cv2 
import numpy as np 
import pyrealsense2 as d435



# _Set queue 
enclosure_queue = Queue() 


# _Configures of depth and color streams 
pipeline = d435.pipeline()
config = d435.config()
config.enable_stream(d435.stream.depth, 640, 480, d435.format.z16, 30)
config.enable_stream(d435.stream.color, 640, 480, d435.format.bgr8, 30)



# _ D435 process 
def D435(queue):
    
    
    print("D435 processing", end="\n ")
    pipeline.start(config) # _Start streaming

    try:
        while True: 
            # _Wait for a coherent pair of frames: depth and color 
            frames = pipeline.wait_for_frames()            
            depth_frame, color_frame = (frames.get_depth_frame(), frames.get_color_frame())

            if not (depth_frame and color_frame): 
                print("Missing frame...", end="\n")
                continue

            # _Convert <pyrealsense2 frame> to <ndarray>
            depth_image = np.asanyarray(depth_frame.get_data()) # convert any array to <ndarray>
            color_image = np.asanyarray(color_frame.get_data())


            # _Apply colormap on depth image 
            #  (image must be converted to 8-bit per pixel first)
            
            
            
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.05), cv2.COLORMAP_BONE)
            #depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.05), cv2.COLORMAP_JET)
            #depth_colormap  = cv2.bitwise_not(depth_colormap ) # reverse image

            #print("Depth map shape = ", depth_colormap.shape)   


            """ Pixelate image 
            (ref) https://stackoverflow.com/questions/55508615/how-to-pixelate-image-using-opencv-in-python
            Applying for 
                         * RGB 
                         * Gray 
            """
            gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)

            H, W = gray.shape 
            pix_w, pix_h = (16, 16) # "pixelated"-size 
                                    # 16 x 16 pixels 

            temp = [color_image, gray]
            out_temp = [cv2.resize(img, (pix_w, pix_h), interpolation=cv2.INTER_LINEAR)  for img in temp]  # downsample 
            output = [cv2.resize(sample, (W, H), interpolation=cv2.INTER_NEAREST) for sample in out_temp]       # upsample 
            output[1] = np.stack((output[1],)*3, axis=-1)   # gray with 3D channel 

            # _End: Pixelate 


            # _Encoding 
            target_frame = depth_colormap
            
            #print(target_frame.shape)
            

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),80]  # 0 ~ 100 quality 
            #encode_param = [cv2.IMWRITE_PNG_COMPRESSION,0] # 0 ~ 9 Compressiong rate 
            #encode_param = [int(cv2.IMWRITE_WEBP_QUALITY),95]  # 0 ~ 100 quality 


            result, imgencode = cv2.imencode('.jpg', target_frame, encode_param)  # Encode numpy into '.jpg'
            data = np.array(imgencode)

            stringData = data.tostring()   # Convert numpy to string
            #print("byte Length: ", len(stringData))
            queue.put(stringData)          # Put the encode in the queue stack


            # __ Image show             
            images1 = np.hstack((color_image, depth_colormap)) # stack both images horizontally            
            images2 = np.hstack((output[0], output[1])) 
            images = np.vstack((images1, images2))
            

            cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
            cv2.imshow('RealSense', images)
            cv2.waitKey(1)        

        
    finally: 
        cv2.destroyAllWindows()

        # _Stop streaming 
        pipeline.stop()

    



class MyTCPHandler(socketserver.BaseRequestHandler):

    queue  = enclosure_queue 
    stringData = str()

    def handle(self):
       
        # 'self.request' is the TCP socket connected to the client     
        print("A client connected by: ", self.client_address[0], ":", self.client_address[1] )


        while True:
            try:
                # _server <- client 
                self.data = self.request.recv(1024).strip()   # 1024 byte for header 
                #print("Received from client: ", self.data)

                if not self.data: 
                    print("The client disconnected by: ", self.client_address[0], ":", self.client_address[1] )     
                    break                

                # _Get data from Queue stack 
                MyTCPHandler.stringData = MyTCPHandler.queue.get()     

                # _server -> client 
                #print(str(len(MyTCPHandler.stringData)).ljust(16).encode())  # <str>.ljust(16) and encode <str> to <bytearray>
                
                ###self.request.sendall(str(len(MyTCPHandler.stringData)).ljust(16).encode())  # <- Make this line ignored when you connect with C# client. 
                self.request.sendall(MyTCPHandler.stringData)  

                
                #self.request.sendall(len(MyTCPHandler.stringData).to_bytes(1024, byteorder= "big"))
                #self.request.sendall(MyTCPHandler.stringData)             

                
            except ConnectionResetError as e: 
                print("The client disconnected by: ", self.client_address[0], ":", self.client_address[1] )     
                break


if __name__ == "__main__":

    # _Webcam process is loaded onto subthread
    start_new_thread(D435, (enclosure_queue,))  
    
    # _Server on
    HOST, PORT = socket.gethostname(), 8080 
    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:    
        
        print("****** Server started ****** ", end="\n \n")     
        
        try: 
            server.serve_forever()
        
        except KeyboardInterrupt as e:
            print("******  Server closed ****** ", end="\n \n" )  
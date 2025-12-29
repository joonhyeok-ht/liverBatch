import numpy as np
import cv2
import SimpleITK as sitk
def ctLoader(path, returnImage=False):
    try:
        reader = sitk.ImageSeriesReader()
        reader.SetImageIO("GDCMImageIO")
        dicomNames = reader.GetGDCMSeriesFileNames(path)
        reader.SetFileNames(dicomNames)
        raw = reader.Execute()
        ct = sitk.GetArrayFromImage(raw)
    except:
        #print("CT load failed!\n\t", path)
        return False
    shape = ct.shape
    spacing = raw.GetSpacing()       # (*pixelSpacing, sliceThickness)
    origin = raw.GetOrigin()
    if returnImage:
        return shape, spacing, origin, ct
    else:
        return shape, spacing
def ctWindowing(ct, _min, _max):
    ct[ct<=_min] = _min
    ct[ct>=_max] = _max
    ct = (ct-_min)/(_max-_min)*255
    return ct
def mm2pix(mm, spacing):
    return int(np.ceil(mm/spacing))
def methodIntensity(ct, spacing, kernelSize=5, roi=None):
    if roi == None:
        axialCrop = [0, ct.shape[0]]
        coronalCrop = [0, ct.shape[1]]
        sagittalCrop = [0, ct.shape[2]]
    else:
        axialCrop = roi[0]
        coronalCrop = roi[1]
        sagittalCrop = roi[2]
    # find roi mask
    mask = np.zeros(shape = ct.shape)
    for i in range(axialCrop[0], axialCrop[1]):
        img = np.uint8(ct[i])
        # img = cv2.erode(img, np.ones((3, 3)))
        # for remove noise
        blur = cv2.GaussianBlur(img, (7, 7), 0)
        # for find contour
        _, thresh = cv2.threshold(blur, 32, 255, cv2.THRESH_BINARY)
        # find contour
        contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        # check find contour
        if len(contours) == 0: return mask
        # find largest contour (whar i find)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        # contour approximation using rdp
        contours[0] = cv2.approxPolyDP(contours[0], 2, True)
        # make slice mask
        sliceMask = np.zeros(shape=img.shape, dtype=np.uint8)
        sliceMask = cv2.drawContours(sliceMask, contours=contours, contourIdx=0, color=(255), thickness=cv2.FILLED, offset=(0, 1))
        sliceMask = cv2.drawContours(sliceMask, contours=contours, contourIdx=0, color=(0), thickness=cv2.FILLED, offset=(0, 10))
        sliceMask[:coronalCrop[0],:] = 0
        sliceMask[coronalCrop[1]:,:] = 0
        sliceMask[:,:sagittalCrop[0]] = 0
        sliceMask[:,sagittalCrop[1]:] = 0
        mask[i] = sliceMask
    ct = ct * (mask/255)
    kernelShape = [mm2pix(kernelSize, spacing[2]), mm2pix(kernelSize, spacing[0]), mm2pix(kernelSize, spacing[1])]
    kernelShape = [k if k%2!=0 else k-1 for k in kernelShape]
    # kernel = [kernelSize+2, kernelSize, kernelSize+2]
    kernel3d = np.ones(shape=(kernelShape))
    output = np.zeros(shape=ct.shape)
    argMax = [0, 0, 0]
    valMax = 0
    # totalSum = 0
    # cnt = 0
    for a in range(axialCrop[0], axialCrop[1]-kernel3d.shape[0]):
        for s in range(sagittalCrop[0], sagittalCrop[1]-kernel3d.shape[1]):
            for c in range(coronalCrop[0], coronalCrop[1]-kernel3d.shape[2]):
                if mask[a, c, s] != 0: break
            output[a, c, s] = np.sum(ct[a:a+kernel3d.shape[0],c:c+kernel3d.shape[1],s:s+kernel3d.shape[2]]*kernel3d)
            # totalSum += output[a, c, s]
            # cnt+=1
            if output[a, c, s] > valMax:
                valMax = output[a, c, s]
                argMax = [int(a+int((kernel3d.shape[0]-1)/2)), int(c+int((kernel3d.shape[1]-1)/2)), int(s+int((kernel3d.shape[2]-1)/2))]
    return argMax, np.mean(np.nonzero(output.reshape(-1)))
def methodContour(ct, spacing, roi = None):
    if roi == None:
        axialCrop = [0, ct.shape[0]]
        coronalCrop = [0, ct.shape[1]]
        sagittalCrop = [0, ct.shape[2]]
    else:
        axialCrop = roi[0]
        coronalCrop = roi[1]
        sagittalCrop = roi[2]
    axialScores = []
    axialPoint = []
    for i in range(axialCrop[0], axialCrop[1]):
        img = np.uint8(ct[i])
        # for remove noise
        img = cv2.erode(img, np.ones((5, 5)))
        blur = cv2.GaussianBlur(img, (7,7), 0)
        # for find contour
        _, thresh = cv2.threshold(blur, 32, 255, cv2.THRESH_BINARY)
        # find contour
        contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        # check find contour
        if len(contours) == 0: return []
        # find largest contour
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        # contour simplify
        contours[0] = cv2.approxPolyDP(contours[0], 2, True)
        contour = contours[0][:,0,:]
        # roi mask
        sliceMask = np.full(shape=img.shape, fill_value=255, dtype=np.uint8)
        sliceMask[:coronalCrop[0],:] = 0
        sliceMask[coronalCrop[1]:,:] = 0
        sliceMask[:,:sagittalCrop[0]] = 0
        sliceMask[:,sagittalCrop[1]:] = 0
        # get masking point
        simplifiedContour = contour[np.array(sliceMask[contour[:,1], contour[:,0]], dtype=bool)]
        scores = []
        for i in range(1, len(simplifiedContour)-1):
            l1 = simplifiedContour[i] - simplifiedContour[i-1]
            l2 = simplifiedContour[i+1] - simplifiedContour[i]
            l1 = l1 / np.linalg.norm(l1)
            l2 = l2 / np.linalg.norm(l2)
            dist = 0
            if  l1[0] <= 0 and l1[1] >= 0 and l2[0] <= 0 and l2[1] <= 0:
                l3 = simplifiedContour[i+1] - simplifiedContour[i-1]
                l3 = l3 / np.linalg.norm(l3)
                p = simplifiedContour[i-1] + l3*np.dot(l3, simplifiedContour[i] - simplifiedContour[i-1])
                p = (p - simplifiedContour[i]) * spacing[:2]
                dist = np.linalg.norm(p) + np.sqrt(np.sum((l1-l2)**2))
                # dist = dist *
                # dist = np.linalg.norm(np.cross(simplifiedContour[i-1]-simplifiedContour[i], simplifiedContour[i+1]-simplifiedContour[i-1]))/np.linalg.norm(simplifiedContour[i+1]-simplifiedContour[i-1]) + np.sqrt(np.sum((l1-l2)**2))
            scores.append(dist)
        if len(scores)>0:
            axialPoint.append(simplifiedContour[np.argmax(scores)+1])
            axialScores.append(np.max(scores))
        else:
            axialPoint.append([0,0])
            axialScores.append(0)
    maxIdx = np.argmax(axialScores)
    navel = [axialPoint[maxIdx][0], axialPoint[maxIdx][1], axialCrop[0]+maxIdx]
    return navel, axialScores[maxIdx]
def predictNavel(ct, spacing, method="both"):
    predicted = [0, 0, 0]
    score = 0
    ct = ctWindowing(ct, -300, 100)
    roi = [int(ct.shape[0]/2-mm2pix(100, spacing[2])), int(ct.shape[0]/2+mm2pix(50, spacing[2]))], \
          [0, int(ct.shape[1]/2)], \
          [int(ct.shape[2]/2-mm2pix(50, spacing[1])), int(ct.shape[2]/2+mm2pix(50, spacing[1]))]
    if method == "contour":
        predicted, score = methodContour(ct, spacing, roi)
    elif method == "intensity":
         predicted, score = methodIntensity(ct, spacing, 5, roi)
    elif method == "both":
        predicted, score = methodContour(ct, spacing, roi)
        method = "contour"
        if score < 7:
            predicted, score = methodIntensity(ct, spacing, 5, roi)
            method = "intensity"
    return predicted, method, score, ct
if __name__=="__main__":
    pp_path="C:/Users/hutom/Desktop/jh_test/data/stomach/01011ug_338_test/dataRoot_stomach_0805_151939/01011ug_338_test/01_DICOM/PP"
    shape, spacing, origin, ct = ctLoader(pp_path,returnImage=True)
    predicted, method, score, ct = predictNavel(ct, spacing, "both")
    print(predicted)
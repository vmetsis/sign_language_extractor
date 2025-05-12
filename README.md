# sign_language_extractor

### Installation
```bash

git clone https://github.com/vmetsis/sign_language_extractor.git

cd sign_language_extractor

docker build -t sign-language-app .
```

### Run the app
```bash
docker run -p 5000:5000 -v "$($PWD.Path)/uploads:/app/uploads" -v "$($PWD.Path)/data:/app/data" --name sign-app-instance sign-language-app
```

### Access the app
Open your web browser and navigate to:
```
http://localhost:5000
```

### Stopping the app
To stop the app, you can use the following command:
```bash
docker stop sign-app-instance
```

#### Note
Before running again:

If the previous docker run command failed but might have partially created the container, it's good practice to remove it first:
```bash
docker rm sign-app-instance
```

This ensures that you start with a clean slate and avoid any potential conflicts with existing containers.


### Modifying the code and re-running
If you modify the code and want to re-run the app, you may need to rebuild the Docker image:
```bash
# 1. Stop the current container (if running)
docker stop sign-app-instance

# 2. Remove the stopped container
docker rm sign-app-instance

# 3. Rebuild the image (crucial!)
docker build -t sign-language-app .

# 4. Run the newly built image
docker run -d -p 5000:5000 -v "$($PWD.Path)/uploads:/app/uploads" -v "$($PWD.Path)/data:/app/data" --name sign-app-instance sign-language-app
```

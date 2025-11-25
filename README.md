# RISC-V Assembler and Simulator

A web-based RISC-V assembler and simulator that allows users to write, assemble, and simulate RISC-V assembly code through a user-friendly interface.

## Features

- Write and edit RISC-V assembly code with syntax highlighting
- Assemble RISC-V code to machine code
- Simulate execution and view register states
- Convert machine code back to assembly
- Pre-loaded example programs (Addition, Multiplication, Fibonacci)
- Real-time error feedback
- Clean and modern web interface

## Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   python app.py
   ```

4. Visit http://localhost:5001 in your browser

## Production Deployment

### Deploying to Render.com

1. Create a new account on [Render.com](https://render.com)

2. Click "New +" and select "Web Service"

3. Connect your GitHub repository

4. Fill in the following details:
   - Name: `risc-v-simulator` (or your preferred name)
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -c gunicorn_config.py app:app`

5. Click "Create Web Service"

The application will be automatically deployed and available at your Render URL.

### Environment Variables

- `PORT`: The port number (set automatically by Render)
- `FLASK_ENV`: Set to 'production' for production deployment

## License

This project is open source and available under the MIT License.



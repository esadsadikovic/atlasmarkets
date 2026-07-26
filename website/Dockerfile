FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY llms.txt /usr/share/nginx/html/llms.txt
RUN mkdir -p /usr/share/nginx/html/static && touch /usr/share/nginx/html/static/favicon.ico
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY dieties.html /usr/share/nginx/html/dieties.html
COPY llms.txt /usr/share/nginx/html/llms.txt
RUN mkdir -p /usr/share/nginx/html/static && touch /usr/share/nginx/html/static/favicon.ico
# Append rewrite rule to existing default.conf's location block.
# We use sed to inject the rewrite right after the existing "location / {" line.
RUN sed -i '/location \/ {/a \    rewrite ^/dieties/?$ /dieties.html last;' /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

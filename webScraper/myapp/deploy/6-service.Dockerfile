FROM nginx:1.21-alpine

COPY ./myapp/deploy/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

FROM registry.cern.ch/cern-sis/base-images/node:10.14.0 as build-stage

WORKDIR /usr/src/app

ENV PATH /usr/src/app/node_modules/.bin:$PATH
COPY . /usr/src/app
RUN yarn
RUN yarn build

FROM registry.cern.ch/cern-sis/base-images/inspirehep/nginx:1.19-with-vts
EXPOSE 8081

COPY docker/nginx/config/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build-stage /usr/src/app/dist /usr/share/nginx/html

ARG VERSION
ENV VERSION="${VERSION}"

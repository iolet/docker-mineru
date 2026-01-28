CUDA_TAG := $(shell grep -v '#' argfile.conf | awk -F '=' '/^CUDA_TAG=*/ { print $$2 }')
CUDA_VER := $(shell grep -v '#' argfile.conf | awk -F '[=-]' '/^CUDA_TAG=*/ { print $$2 }')
MINERU_VER := $(shell grep -v '#' requirements.txt | awk -F '=' '/^mineru[~><=].=*/ { print $$2 }')

rev := $(shell git show --no-patch --date=format:%Y%m%d --pretty=format:%cd.%h HEAD)
tag := $(MINERU_VER)-cuda$(CUDA_VER)-rev$(rev)
img := iolet/mineru:$(tag)

src := $(shell find src -type f -path 'src/*' -not -name '*.pyc') \
       $(shell find patches -type f -name '*.patch') \
	   .env.example .flaskenv gunicorn.conf.py mineru.json.template requirements.txt \
       .containerignore argfile.conf entrypoint.sh Containerfile
dst := $(subst :,@,$(subst /,--,$(img))).tar.zst


.PHONY: tarball
tarball: $(dst)

$(dst): $(src)
	podman build \
            --build-arg-file argfile.conf \
            --annotation org.opencontainers.image.base.name=$(shell awk -f image.awk Containerfile):$(CUDA_TAG) \
            --annotation org.opencontainers.image.created=$(shell date --utc '+%FT%H:%M:%SZ') \
            --annotation org.opencontainers.image.revision=$(shell git rev-parse HEAD) \
            --tag $(img) \
            .
	podman save $(img) | zstd - > $(dst)

.PHONY: clean
clean:
	-rm --force *.tar.gz *.tar.zst *.log
	podman image exists $(img) && podman image rm $(img)

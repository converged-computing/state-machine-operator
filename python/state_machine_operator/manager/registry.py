import os
from logging import getLogger

import oras.defaults
import oras.oci
import oras.provider
import oras.utils as utils
from oras.decorator import ensure_container

# This is a custom OCI registry that can be implemented by various components
# to push / pull artifacts using the oras client https://oras.land.
# It requires oras to be installed (pip install oras) and thus
# should not be imported by default


LOGGER = getLogger(__name__)


class RegistryArtifact:
    """
    A RegistryArtifact holds a set of content types and objects to upload
    to a registry.
    """

    def __init__(self, annotations=None):
        self.archives = {}
        self.titles = {}
        self.annotations = annotations or {}

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "[registry-artifact]"

    def remove(self):
        """
        Delete artifact files.

        TODO: when the mlserver is running as a service we likely will
        want to delete the artifacts after we upload them.
        Loic - is there a reason to keep them?
        """
        pass

    def push(self, target, tls_verify=None, plain_http=None):
        """
        Push archives to a target
        """
        reg = get_oras_client(tls_verify, plain_http)
        reg.push(target, self.archives, self.annotations, titles=self.titles)

    def summary(self):
        """
        Print a summary of files to uploiad
        """
        LOGGER.info("Generated %s artifacts" % len(self.archives))
        for path, mediaType in self.archives.items():
            LOGGER.info("%s %s" % (mediaType.ljust(25), path))

    def add_title(self, path, title):
        """
        Add a specific title for a blob.
        """
        self.titles[path] = title

    def add_archive(self, path, mediaType):
        """
        Add an archive to the build result
        """
        self.archives[path] = mediaType


def get_oras_client(tls_verify=None, plain_http=None):
    """
    Consistent method to get an oras client
    """
    # Default to secure with https
    if tls_verify is None:
        tls_verify = True
    if plain_http is None:
        plain_http = False

    user = os.environ.get("ORAS_USER")
    password = os.environ.get("ORAS_PASS")
    reg = Registry(insecure=plain_http, tls_verify=tls_verify)
    if user and password:
        print("Found username and password for basic auth")
        reg.set_basic_auth(user, password)
    return reg


def generate_uri(host, name, tag=None):
    """
    Consistent way to assemble a host and artifact name, tag.
    """
    # Please don't use latest
    tag = tag or "latest"

    # The name must be lowercase. We can do more cleaning here if necessary
    name = name.lower()
    return f"{host}/{name}:{tag}"


class Registry(oras.provider.Registry):
    @ensure_container
    def push(self, container, archives: dict, annotations=None, titles: dict = None):
        """
        Given a dict of layers (paths and corresponding mediaType) push.
        """
        # Lookup of titles to override default
        titles = titles or {}

        # Prepare a new manifest
        manifest = oras.oci.NewManifest()

        # A lookup of annotations we can add
        annotset = oras.oci.Annotations(annotations or {})
        LOGGER.info(f"Preparing to push {archives} to {container}")

        # Upload files as blobs
        for blob, mediaType in archives.items():
            # Must exist
            if not os.path.exists(blob):
                raise ValueError(f"{blob} does not exist.")

            # Save directory or blob name before compressing
            blob_name = os.path.basename(blob)
            if blob in titles:
                blob_name = titles[blob]

            # If it's a directory, we need to compress
            cleanup_blob = False
            if os.path.isdir(blob):
                blob = oras.utils.make_targz(blob)
                cleanup_blob = True

            # Create a new layer from the blob
            layer = oras.oci.NewLayer(blob, mediaType, is_dir=cleanup_blob)
            annotations = annotset.get_annotations(blob)
            layer["annotations"] = {oras.defaults.annotation_title: blob_name}
            if annotations:
                layer["annotations"].update(annotations)

            # update the manifest with the new layer
            manifest["layers"].append(layer)

            # Upload the blob layer
            LOGGER.info(f"Uploading {blob} to {container.uri}")
            response = self.upload_blob(blob, container, layer)
            self._check_200_response(response)

            # Do we need to cleanup a temporary targz?
            if cleanup_blob and os.path.exists(blob):
                os.remove(blob)

        # Add annotations to the manifest, if provided
        manifest_annots = annotset.get_annotations("$manifest")
        if manifest_annots:
            manifest["annotations"] = manifest_annots

        # Prepare the manifest config (temporary or one provided)
        config_annots = annotset.get_annotations("$config")
        conf, config_file = oras.oci.ManifestConfig()

        # Config annotations?
        if config_annots:
            conf["annotations"] = config_annots

        # Config is just another layer blob, this is an empty file
        if config_file is None:
            config_file = utils.get_tmpfile(prefix="config-", suffix=".json")
            utils.write_file(config_file, "{}")
        response = self.upload_blob(config_file, container, conf)
        self._check_200_response(response)

        # Final upload of the manifest
        manifest["config"] = conf
        self._check_200_response(self.upload_manifest(manifest, container))
        LOGGER.info(f"Successfully pushed {container}")
        return response

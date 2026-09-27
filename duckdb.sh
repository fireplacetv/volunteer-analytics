#!/bin/sh -e

# DuckDB Linux/OSX installer script, revision $Id: 50350db8c350a16cee7c2ab1cfc33689ba33b816 $
# Issues/PRs for this script: https://github.com/duckdb/duckdb-install-scripts

main () {
    OS=$(uname -s)
    ARCH=$(uname -m)

    command -v curl >/dev/null 2>&1 || { echo >&2 "Required tool curl could not be found. Aborting."; exit 1; }
    command -v zcat >/dev/null 2>&1 || { echo >&2 "Required tool zcat could not be found. Hint: install the gzip package. Aborting."; exit 1; }
    command -v tar >/dev/null 2>&1 || { echo >&2 "Required tool tar could not be found. Aborting."; exit 1; }

    DUCKDB_STAGED="${DUCKDB_STAGED:-}"
    if [ -z "${DUCKDB_STAGED}" ] && [ "${DUCKDB_VERSION:-}" = "alpha" ]
    then
        if ! DUCKDB_STAGED=$(curl --fail --silent --show-error https://duckdb-staging.duckdb.org/latest_alpha_version.txt)
        then
            echo "Failed to determine the latest DuckDB alpha version." 1>&2
            exit 1
        fi
    fi

    LATEST_VER=
    if [ -n "${DUCKDB_STAGED}" ]
    then
        VER="${DUCKDB_STAGED#*/}"
        STAGED_COMMIT=$(printf '%.10s' "${DUCKDB_STAGED%%/*}")
        DUCKDB_STAGED="${STAGED_COMMIT}/${VER}"
    else
        LATEST_VER=$(curl --fail --silent --show-error https://duckdb.org/data/latest_stable_version.txt)

        # figure out latest version or use the one from the environment
        if [ -z "${DUCKDB_VERSION:-}" ]
        then
            VER=$LATEST_VER
        else
            VER="$DUCKDB_VERSION"
        fi
    fi
    
    PREFIX="${HOME}/.duckdb/cli"
    INST="${PREFIX}/${VER}"
    LATEST="${PREFIX}/latest"
    UPDATE_LATEST=false
    if [ -n "${DUCKDB_STAGED}" ] || [ "${VER}" = "${LATEST_VER}" ]
    then
        UPDATE_LATEST=true
    fi

    DIST=

    if [ "${OS}" = "Linux" ]
    then
        if [ "${ARCH}" = "x86_64" ] || [ "${ARCH}" = "amd64" ]
        then
            DIST=linux-amd64
        elif [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]
        then
            DIST=linux-arm64
        fi

        if [ -n "${DIST}" ] && ldd --version 2>&1 | grep -qi musl
        then
            DIST="${DIST}-musl"
        fi
    elif [ "${OS}" = "Darwin" ]
    then
        if [ "${ARCH}" = "x86_64" ]
        then
            DIST=osx-amd64
        elif [ "${ARCH}" = "arm64" ]
        then
            DIST=osx-arm64
        fi
    fi

    if [ -z "${DIST}" ]
    then
        echo "Operating system '${OS}' / architecture '${ARCH}' is unsupported." 1>&2
        exit 1
    fi

    extract_v1() {
        URL="https://install.duckdb.org/v${VER}/duckdb_cli-${DIST}.gz"
        curl --fail --location --progress-bar "${URL}" -o- | zcat > "$1" || exit 1
        chmod a+x "$1"
    }

    extract_v2() {
        if [ -n "${DUCKDB_STAGED}" ]
        then
            URL="https://duckdb-staging.duckdb.org/${DUCKDB_STAGED}/duckdb/duckdb/github_release/duckdb-cli-${DIST}.tar.gz"
        else
            URL="https://install.duckdb.org/v${VER}/duckdb-cli-${DIST}.tar.gz"
        fi
        curl --fail --location --progress-bar "${URL}" | tar -C "$1" -xzf - || exit 1
    }

    echo
    echo "*** DuckDB Linux/MacOS installation script, version ${VER} ***"
    echo
    echo
    echo "         .;odxdl,            "
    echo "       .xXXXXXXXXKc          "
    echo "       0XXXXXXXXXXXd  cooo:  "
    echo "      ,XXXXXXXXXXXXK  OXXXXd "
    echo "       0XXXXXXXXXXXo  cooo:  "
    echo "       .xXXXXXXXXKc          "
    echo "         .;odxdl,  "
    echo 
    echo

    test_installed_duckdb() {
        "${INST}/duckdb" -noheader -init /dev/null -csv -batch -s "SELECT 2*3*7" 2>/dev/null
    }

    if [ -f "${INST}/duckdb" ] && [ "$(test_installed_duckdb)" = "42" ]; then
        echo "Destination binary ${INST}/duckdb already exists and seems to work"
    else  
        mkdir -p "${INST}"

        if [ ! -d "${INST}" ]; then
            echo "Failed to create install directory ${INST}." 1>&2
            exit 1
        fi

        if [ -z "${DUCKDB_STAGED}" ]; then
            case "${VER}" in
                1*) extract_v1 "${INST}/duckdb" ;;
                *) extract_v2 "${INST}" ;;
            esac
        else
            extract_v2 "${INST}"
        fi

        if [ ! -f "${INST}/duckdb" ]; then
            echo "Failed to download/unpack binary at ${INST}/duckdb" 1>&2
            exit 1
        fi

        # lets test if this works
        if [ "$(test_installed_duckdb)" != "42" ]; then
            echo "Failed to execute installed binary :/ ${INST}." 1>&2
            exit 1  
        fi
        echo
        echo "Successfully installed DuckDB ${VER} to ${INST}/duckdb"
    fi

    if [ "${UPDATE_LATEST}" = true ] ; then
        # update symlink
         rm -f "${LATEST}" || exit 1
        ln -s "${INST}" "${LATEST}" || exit 1
        echo "Updated symlink from ${LATEST}/duckdb to"
        echo "                     ${INST}/duckdb"

        echo
        echo "Hint: Append the following line to your shell profile:"
        printf "export PATH=\"%s\":\$PATH\n" "${LATEST}"
    else
        echo
        echo "Hint: Append the following line to your shell profile:"
        printf "export PATH=\"%s\":\$PATH\n" "${INST}"
    fi

    # maybe ~/.local/bin exists and is writeable and does not have duckdb yet
    # if so, symlink
    LOCALBIN="${HOME}/.local/bin"
    if [ "${UPDATE_LATEST}" = true ] && [ -d "${LOCALBIN}" ] && [ -w "${LOCALBIN}" ] && [ ! -f "${LOCALBIN}/duckdb" ]; then
        ln -s "${LATEST}/duckdb" "${LOCALBIN}/duckdb" || exit 1
        echo "Also created a symlink from ${LOCALBIN}/duckdb 
                         to ${LATEST}/duckdb"
    fi

    echo
    echo "To launch DuckDB ${VER} now, type"
    if [ "${UPDATE_LATEST}" = true ] ; then
        echo "${LATEST}/duckdb"
    else
        echo "${INST}/duckdb"
    fi
}

main

#!/bin/sh

# 1️⃣ Git repo rootiga o‘tamiz
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT" || { echo "Not a git repo"; exit 1; }

# 2️⃣ Commit message
MSG="$*"
[ -z "$MSG" ] && echo "Commit message required" && exit 1

# 3️⃣ Branch aniqlash
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$BRANCH" = "main" ]; then
    FILE="main_v.txt"
else
    git commit -m "$MSG"
    exit 0
fi

# 4️⃣ Fayl mavjudligi tekshirish
if [ ! -f "$FILE" ]; then
    echo "v 1.0.0 => $BRANCH: $MSG" > "$FILE"
else
    LAST=$(head -n 1 "$FILE")
    VER=$(echo "$LAST" | sed 's/v //; s/ =>.*//')

    MAJOR=$(echo "$VER" | cut -d. -f1)
    MINOR=$(echo "$VER" | cut -d. -f2)
    PATCH=$(echo "$VER" | cut -d. -f3)

    PATCH=$((PATCH + 1))
    if [ "$PATCH" -gt 9 ]; then
        PATCH=0
        MINOR=$((MINOR + 1))
    fi
    if [ "$MINOR" -gt 9 ]; then
        MINOR=0
        MAJOR=$((MAJOR + 1))
    fi

    TMP=$(mktemp)
    echo "v $MAJOR.$MINOR.$PATCH => $BRANCH: $MSG" > "$TMP"
    cat "$FILE" >> "$TMP"
    mv "$TMP" "$FILE"
fi

# 5️⃣ Git add + commit
git add "$FILE"
git commit -m "$MSG"

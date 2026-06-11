#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Pipecat entry shim. Business code lives under app/."""

from app.bot import bot  # noqa: F401

if __name__ == "__main__":
    from pipecat.runner.run import main

    main()

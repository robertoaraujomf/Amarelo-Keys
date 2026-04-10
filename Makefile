.PHONY: deb clean

deb:
	@echo "Building Debian package..."
	@rm -rf deb
	@mkdir -p deb/amarelo-keys/DEBIAN
	@mkdir -p deb/amarelo-keys/usr/share/amarelo-keys
	@mkdir -p deb/amarelo-keys/usr/share/applications
	@mkdir -p deb/amarelo-keys/usr/bin
	@mkdir -p deb/amarelo-keys/etc/xdg/autostart
	@cp -r src/amarelo_keys deb/amarelo-keys/usr/share/amarelo-keys/
	@cp data/amarelo-keys.desktop deb/amarelo-keys/usr/share/applications/
	@cp data/autostart.desktop deb/amarelo-keys/etc/xdg/autostart/amarelo-keys.desktop
	@printf '#!/usr/bin/env python3\nimport sys\nsys.path.insert(0, "/usr/share/amarelo-keys")\nfrom amarelo_keys.__main__ import main\nmain()' > deb/amarelo-keys/usr/bin/amarelo-keys
	@chmod 755 deb/amarelo-keys/usr/bin/amarelo-keys
	@echo "Package: amarelo-keys" > deb/amarelo-keys/DEBIAN/control
	@echo "Version: 1.0.0" >> deb/amarelo-keys/DEBIAN/control
	@echo "Section: utils" >> deb/amarelo-keys/DEBIAN/control
	@echo "Priority: optional" >> deb/amarelo-keys/DEBIAN/control
	@echo "Architecture: all" >> deb/amarelo-keys/DEBIAN/control
	@echo "Depends: python3 (>= 3.10), python3-pynput" >> deb/amarelo-keys/DEBIAN/control
	@echo "Maintainer: Amarelo Software" >> deb/amarelo-keys/DEBIAN/control
	@echo "Description: Keyboard remapping utility" >> deb/amarelo-keys/DEBIAN/control
	@echo " Helps users with defective keyboards by allowing custom key combinations." >> deb/amarelo-keys/DEBIAN/control
	@dpkg-deb --build deb/amarelo-keys dist/amarelo-keys_1.0.0_all.deb
	@rm -rf deb
	@echo ""
	@echo "Package created: dist/amarelo-keys_1.0.0_all.deb"

clean:
	rm -f dist/amarelo-keys_1.0.0_all.deb

import ifcopenshell.api
from pathlib import Path
from ifcopenshell.util.shape_builder import ShapeBuilder, V
import importlib
import sys
from csv import DictReader

root_dir=Path(__file__).parents[1]
lib_dir=root_dir / 'lib'
sys.path.append(str(lib_dir))

library_name="default_library"
library=importlib.import_module(library_name)
#importlib.reload(library)

csv_filename="data.csv"
csv_filepath=lib_dir / csv_filename

class LibraryGenerator:
    def generate(self, output_filename="IFC4 Library.ifc"):
        ifcopenshell.api.pre_listeners = {}
        ifcopenshell.api.post_listeners = {}

        self.materials = {}

        self.file = ifcopenshell.api.run("project.create_file")
        self.project = ifcopenshell.api.run(
            "root.create_entity", self.file, ifc_class="IfcProject", name=f"Non-structural assets library"
        )
        self.library = ifcopenshell.api.run(
            "root.create_entity", self.file, ifc_class="IfcProjectLibrary", name=f"Non-structural assets library"
        )
        ifcopenshell.api.run(
            "project.assign_declaration", self.file, definition=self.library, relating_context=self.project
        )
        unit = ifcopenshell.api.run("unit.add_si_unit", self.file, unit_type="LENGTHUNIT", prefix="MILLI")
        ifcopenshell.api.run("unit.assign_unit", self.file, units=[unit])

        model = ifcopenshell.api.run("context.add_context", self.file, context_type="Model")
        plan = ifcopenshell.api.run("context.add_context", self.file, context_type="Plan")
        self.representations = {
            "model_body": ifcopenshell.api.run(
                "context.add_context",
                self.file,
                context_type="Model",
                context_identifier="Body",
                target_view="MODEL_VIEW",
                parent=model,
            ),
            "plan_body": ifcopenshell.api.run(
                "context.add_context",
                self.file,
                context_type="Plan",
                context_identifier="Body",
                target_view="PLAN_VIEW",
                parent=plan,
            ),
        }

        builder = ShapeBuilder(self.file)

        with open(csv_filepath, 'r') as csvfile:
            dict_reader = DictReader(csvfile, delimiter=',')
            list_of_objects = list(dict_reader)

        for object_data in list_of_objects:
            try: 
                builder_function = getattr(library, object_data["f"])
                builder_function_argcount=builder_function.__code__.co_argcount
                builder_function_args=builder_function.__code__.co_varnames[:builder_function_argcount]
                arg_to_pass=[]
                object_data["builder"]=builder
                object_data["self"]=self
                for arg in builder_function_args:
                    try:
                        object_data[arg]=float(object_data[arg])
                    except (TypeError, ValueError):
                        pass
                    arg_to_pass.append(object_data[arg])
                representation_3d, representation_2d = builder_function(*arg_to_pass)
                self.create_explicit_type(
                    "IfcFurnitureType", object_data["name"], representation_3d, representation_2d
                )
                print(object_data["name"]+" created with "+object_data["f"])
            except AttributeError:
                print(object_data["f"]+" is not a function in the library.")

        self.file.write(output_filename)

    def create_explicit_type(self, ifc_class, name, representation_3d, representation_2d, **params):
        element = ifcopenshell.api.run("root.create_entity", self.file, ifc_class=ifc_class, name=name)
        for param, value in params.items():
            setattr(element, param, value)

        ifcopenshell.api.run(
            "geometry.assign_representation", self.file, product=element, representation=representation_3d
        )
        ifcopenshell.api.run(
            "geometry.assign_representation", self.file, product=element, representation=representation_2d
        )
        ifcopenshell.api.run("project.assign_declaration", self.file, definition=element, relating_context=self.library)
        return element

if __name__ == "__main__":
    path = Path(__file__).parents[1] / "IFC_Library"
    LibraryGenerator().generate(output_filename=str(path / "IFC4 CSV Library.ifc"))
